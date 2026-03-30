# controllers/ga_optimizer.py
import random
from PyQt5.QtCore import QTime


class GAOptimizer:
    def __init__(self, stations, section_times):
        self.stations = stations
        self.section_times = section_times

        # ================= 论文推荐的最优参数 =================
        self.POP_SIZE = 101  # 种群大小
        self.MAX_GEN = 300  # 进化代数

        # 自适应概率的基础系数 (依据论文式 4-7, 4-8)
        self.K_C = 0.8  # 基础交叉概率
        self.K_M = 0.1  # 基础变异概率
        # ======================================================

    def optimize_dispatch_order(self, current_station_id, next_station_id, delayed_trains):
        """
        单一遗传算法主入口：针对发生晚点的车站，求解去往下一站的最优发车顺序
        """
        if len(delayed_trains) <= 1:
            return delayed_trains  # 只有一辆车不需要调整

        # 1. 种群初始化
        population = self._initialize_population(delayed_trains)

        best_individual = None
        best_fitness = -1.0

        for generation in range(self.MAX_GEN):
            # 2. 计算适应度
            fitness_list = []
            for ind in population:
                fit = self._calculate_fitness(ind, current_station_id, next_station_id, delayed_trains)
                fitness_list.append(fit)

                if fit > best_fitness:
                    best_fitness = fit
                    best_individual = ind.copy()

            f_max = max(fitness_list)
            f_avg = sum(fitness_list) / len(fitness_list)

            # 终止条件判断：种群适应度收敛 (论文式 4-6)
            convergence = sum(abs(f - f_avg) for f in fitness_list)
            if convergence <= 0.001:
                break

            # 3. 轮盘赌选择
            new_population = self._selection(population, fitness_list)

            # 4. 顺序交叉 (含自适应概率)
            new_population = self._crossover(new_population, fitness_list, f_max, f_avg)

            # 5. 两点交换变异 (含自适应概率)
            new_population = self._mutation(new_population, fitness_list, f_max, f_avg)

            # 6. 启发式纠错 (修复违反车站越行约束的非法解)
            for i in range(len(new_population)):
                new_population[i] = self._heuristic_repair(new_population[i], delayed_trains)

        # 按照最优染色体解码，返回重排后的列车对象列表
        return [delayed_trains[idx] for idx in best_individual]

    def _initialize_population(self, delayed_trains):
        # 初始发车顺序序列，如 [0, 1, 2, 3]
        base_seq = list(range(len(delayed_trains)))
        pop = [base_seq.copy()]  # 必须保留一个原始发车顺序作为底座
        for _ in range(self.POP_SIZE - 1):
            shuffled = base_seq.copy()
            random.shuffle(shuffled)
            pop.append(shuffled)
        return pop

    def _selection(self, population, fitness_list):
        total_fit = sum(fitness_list)
        if total_fit == 0: return population.copy()

        cum_probs = []
        current_sum = 0.0
        for f in fitness_list:
            current_sum += f / total_fit
            cum_probs.append(current_sum)

        new_pop = []
        # 精英保留策略：直接把当代适应度最高的个体无损放入下一代
        best_idx = fitness_list.index(max(fitness_list))
        new_pop.append(population[best_idx].copy())

        # 轮盘赌选择剩下的个体
        for _ in range(self.POP_SIZE - 1):
            r = random.random()
            for i, cp in enumerate(cum_probs):
                if r <= cp:
                    new_pop.append(population[i].copy())
                    break
        return new_pop

    def _crossover(self, population, fitness_list, f_max, f_avg):
        new_pop = [population[0]]  # 精英个体直接遗传

        for i in range(1, len(population), 2):
            ind1 = population[i].copy()
            ind2 = population[i + 1].copy() if i + 1 < len(population) else population[1].copy()

            # 计算自适应交叉概率 Pc (论文式 4-7)
            fc = max(fitness_list[i], fitness_list[i + 1] if i + 1 < len(fitness_list) else fitness_list[1])
            if fc <= f_avg or f_max == f_avg:
                pc = self.K_C
            else:
                pc = self.K_C * (f_max - fc) / (f_max - f_avg)

            if random.random() < pc:
                # 执行顺序交叉 (Order Crossover)
                pt1, pt2 = sorted(random.sample(range(len(ind1)), 2))
                child1 = self._order_crossover(ind1, ind2, pt1, pt2)
                child2 = self._order_crossover(ind2, ind1, pt1, pt2)
                new_pop.extend([child1, child2])
            else:
                new_pop.extend([ind1, ind2])

        return new_pop[:self.POP_SIZE]

    def _order_crossover(self, parent1, parent2, pt1, pt2):
        size = len(parent1)
        child = [None] * size

        # 保留交叉点之间的基因
        child[pt1:pt2 + 1] = parent1[pt1:pt2 + 1]

        # 填入剩余基因
        curr_idx = (pt2 + 1) % size
        p2_idx = (pt2 + 1) % size

        while None in child:
            if parent2[p2_idx] not in child:
                child[curr_idx] = parent2[p2_idx]
                curr_idx = (curr_idx + 1) % size
            p2_idx = (p2_idx + 1) % size

        return child

    def _mutation(self, population, fitness_list, f_max, f_avg):
        new_pop = [population[0]]  # 精英不参与变异

        for i in range(1, len(population)):
            ind = population[i].copy()
            fm = fitness_list[i]

            # 自适应变异概率 Pm (论文式 4-8)
            if fm <= f_avg or f_max == f_avg:
                pm = self.K_M
            else:
                pm = self.K_M * (f_max - fm) / (f_max - f_avg)

            if random.random() < pm:
                # 执行两点交换变异
                pt1, pt2 = random.sample(range(len(ind)), 2)
                ind[pt1], ind[pt2] = ind[pt2], ind[pt1]

            new_pop.append(ind)
        return new_pop

    def _heuristic_repair(self, chromosome, delayed_trains):
        """
        核心防撞机制：启发式纠错 (剥离 -> 推延 -> 回填)
        确保同等级不互越，高等级绝对优先
        """
        high_level_trains = []
        low_level_trains = []

        for train_idx in chromosome:
            train_obj = delayed_trains[train_idx]
            if self._get_train_grade(train_obj.train_number) >= 3:
                high_level_trains.append(train_idx)
            else:
                low_level_trains.append(train_idx)

        repaired_chromosome = [None] * len(chromosome)

        for low_idx in low_level_trains:
            overtaken_count = 0
            for i in range(chromosome.index(low_idx)):
                if chromosome[i] in high_level_trains and chromosome[i] > low_idx:
                    overtaken_count += 1

            new_pos = low_idx + overtaken_count
            while new_pos < len(repaired_chromosome) and repaired_chromosome[new_pos] is not None:
                new_pos += 1

            if new_pos < len(repaired_chromosome):
                repaired_chromosome[new_pos] = low_idx

        high_level_trains.sort()
        high_idx = 0
        for i in range(len(repaired_chromosome)):
            if repaired_chromosome[i] is None:
                if high_idx < len(high_level_trains):
                    repaired_chromosome[i] = high_level_trains[high_idx]
                    high_idx += 1
                else:
                    repaired_chromosome[i] = low_level_trains[0] if low_level_trains else 0

        return repaired_chromosome

    def _calculate_fitness(self, chromosome, current_station_id, next_station_id, delayed_trains):
        """
        论文目标函数：区段总加权到达晚点时间的倒数
        """
        total_weighted_delay = 0.0
        last_departure_mins = -999

        for train_idx in chromosome:
            train = delayed_trains[train_idx]
            weight = 0.3 if self._get_train_grade(train.train_number) >= 3 else 0.1

            curr_pt = next((p for p in train.points if p.station_id == current_station_id), None)
            next_pt = next((p for p in train.points if p.station_id == next_station_id), None)

            if not curr_pt or not next_pt: continue

            # 假定此时 planned_departure 已经被注入了初始晚点时间
            ready_to_dep_mins = self._time_to_mins(curr_pt.planned_departure)

            # 追踪间隔约束推算：发车必须留足 3 分钟安全追踪间隔
            actual_dep_mins = max(ready_to_dep_mins, last_departure_mins + 3)
            last_departure_mins = actual_dep_mins

            # 区间最小运行时分约束 (动态查表)
            run_time = self.section_times.get((current_station_id, next_station_id), 4)
            actual_arr_next_mins = actual_dep_mins + run_time

            planned_arr_next_mins = self._time_to_mins(next_pt.planned_arrival)
            delay = max(0, actual_arr_next_mins - planned_arr_next_mins)

            total_weighted_delay += delay * weight

        if total_weighted_delay == 0:
            return 99999.0  # 无晚点，适应度极大
        return 1.0 / total_weighted_delay

    def _time_to_mins(self, qt):
        return qt.hour() * 60 + qt.minute() if qt else 0

    def _get_train_grade(self, train_num):
        prefix = str(train_num)[0].upper()
        if prefix == 'G': return 4
        if prefix == 'D': return 3
        if prefix == 'C': return 2
        return 1