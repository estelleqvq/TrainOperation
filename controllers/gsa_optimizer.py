# controllers/gsa_optimizer.py
import random
import math
from PyQt5.QtCore import QTime


class GSAOptimizer:
    def __init__(self, stations, section_times):
        self.stations = stations
        self.section_times = section_times

        # ================= 1. 遗传算法(GA)基础参数 =================
        self.POP_SIZE = 101
        self.K_C = 0.8
        self.K_M = 0.1

        # ================= 2. 模拟退火(SA)扩展参数 =================
        self.INITIAL_TEMP = 1200.0
        self.MIN_TEMP = 1.2
        self.COOLING_RATE = 0.98
        self.ITERATIONS_PER_TEMP = 5

    def optimize_dispatch_order(self, current_station_id, next_station_id, delayed_trains):
        if len(delayed_trains) <= 1:
            return delayed_trains, 0.0, 0

        population = self._initialize_population(delayed_trains)
        best_individual = None
        best_fitness = -1.0

        current_temp = self.INITIAL_TEMP

        while current_temp > self.MIN_TEMP:
            fitness_list = []
            for ind in population:
                fit = self._calculate_fitness(ind, current_station_id, next_station_id, delayed_trains)
                fitness_list.append(fit)
                if fit > best_fitness:
                    best_fitness = fit
                    best_individual = ind.copy()

            f_max = max(fitness_list)
            f_avg = sum(fitness_list) / len(fitness_list)

            new_population = self._selection(population, fitness_list)
            new_population = self._crossover(new_population, fitness_list, f_max, f_avg)
            new_population = self._mutation(new_population, fitness_list, f_max, f_avg)

            for i in range(len(new_population)):
                new_population[i] = self._heuristic_repair(new_population[i], delayed_trains)

            for _ in range(self.ITERATIONS_PER_TEMP):
                for i in range(len(new_population)):
                    current_ind = new_population[i]
                    current_fit = self._calculate_fitness(current_ind, current_station_id, next_station_id,
                                                          delayed_trains)

                    neighbor_ind = self._sa_disturbance(current_ind.copy())
                    neighbor_ind = self._heuristic_repair(neighbor_ind, delayed_trains)
                    neighbor_fit = self._calculate_fitness(neighbor_ind, current_station_id, next_station_id,
                                                           delayed_trains)

                    if self._metropolis_accept(current_fit, neighbor_fit, current_temp):
                        new_population[i] = neighbor_ind

            population = new_population
            current_temp *= self.COOLING_RATE

        # ====== 计算真实的纯晚点时间和波及列车数 (不含惩罚项) ======
        pure_section_delay = 0.0
        pure_adjusted_count = 0
        last_dep = -999

        for train_idx in best_individual:
            t = delayed_trains[train_idx]
            w = 0.3 if self._get_train_grade(t.train_number) >= 3 else 0.1
            cp = next((p for p in t.points if p.station_id == current_station_id), None)
            np = next((p for p in t.points if p.station_id == next_station_id), None)

            if cp and np:
                rd = self._time_to_mins(cp.planned_departure)
                ad = max(rd, last_dep + 3)
                last_dep = ad
                rt = self.section_times.get((current_station_id, next_station_id), 4)
                arr = ad + rt
                plan_arr = self._time_to_mins(np.planned_arrival)
                dl = max(0, arr - plan_arr)
                pure_section_delay += dl * w
                if dl > 0:
                    pure_adjusted_count += 1

        return [delayed_trains[idx] for idx in best_individual], pure_section_delay, pure_adjusted_count

    def _sa_disturbance(self, chromosome):
        if len(chromosome) < 2: return chromosome
        pt1, pt2 = random.sample(range(len(chromosome)), 2)
        chromosome[pt1], chromosome[pt2] = chromosome[pt2], chromosome[pt1]
        return chromosome

    def _metropolis_accept(self, current_fit, neighbor_fit, current_temp):
        if neighbor_fit >= current_fit:
            return True
        else:
            delta_f = neighbor_fit - current_fit
            probability = math.exp(delta_f / current_temp)
            return random.random() < probability

    def _initialize_population(self, delayed_trains):
        base_seq = list(range(len(delayed_trains)))
        pop = [base_seq.copy()]
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
        best_idx = fitness_list.index(max(fitness_list))
        new_pop.append(population[best_idx].copy())
        for _ in range(self.POP_SIZE - 1):
            r = random.random()
            for i, cp in enumerate(cum_probs):
                if r <= cp:
                    new_pop.append(population[i].copy())
                    break
        return new_pop

    def _crossover(self, population, fitness_list, f_max, f_avg):
        new_pop = [population[0]]
        for i in range(1, len(population), 2):
            ind1, ind2 = population[i].copy(), (
                population[i + 1].copy() if i + 1 < len(population) else population[1].copy())
            fc = max(fitness_list[i], fitness_list[i + 1] if i + 1 < len(fitness_list) else fitness_list[1])
            pc = self.K_C if (fc <= f_avg or f_max == f_avg) else self.K_C * (f_max - fc) / (f_max - f_avg)
            if random.random() < pc:
                pt1, pt2 = sorted(random.sample(range(len(ind1)), 2))
                new_pop.extend(
                    [self._order_crossover(ind1, ind2, pt1, pt2), self._order_crossover(ind2, ind1, pt1, pt2)])
            else:
                new_pop.extend([ind1, ind2])
        return new_pop[:self.POP_SIZE]

    def _order_crossover(self, parent1, parent2, pt1, pt2):
        size = len(parent1)
        child = [None] * size
        child[pt1:pt2 + 1] = parent1[pt1:pt2 + 1]
        curr_idx, p2_idx = (pt2 + 1) % size, (pt2 + 1) % size
        while None in child:
            if parent2[p2_idx] not in child:
                child[curr_idx] = parent2[p2_idx]
                curr_idx = (curr_idx + 1) % size
            p2_idx = (p2_idx + 1) % size
        return child

    def _mutation(self, population, fitness_list, f_max, f_avg):
        new_pop = [population[0]]
        for i in range(1, len(population)):
            ind, fm = population[i].copy(), fitness_list[i]
            pm = self.K_M if (fm <= f_avg or f_max == f_avg) else self.K_M * (f_max - fm) / (f_max - f_avg)
            if random.random() < pm:
                pt1, pt2 = random.sample(range(len(ind)), 2)
                ind[pt1], ind[pt2] = ind[pt2], ind[pt1]
            new_pop.append(ind)
        return new_pop

    def _heuristic_repair(self, chromosome, delayed_trains):
        high_pos, low_pos, high_vals, low_vals = [], [], [], []
        for i, train_idx in enumerate(chromosome):
            train_obj = delayed_trains[train_idx]
            if self._get_train_grade(train_obj.train_number) >= 3:
                high_pos.append(i);
                high_vals.append(train_idx)
            else:
                low_pos.append(i);
                low_vals.append(train_idx)
        high_vals.sort();
        low_vals.sort()
        repaired = [None] * len(chromosome)
        for i, pos in enumerate(high_pos): repaired[pos] = high_vals[i]
        for i, pos in enumerate(low_pos): repaired[pos] = low_vals[i]
        return repaired

    def _calculate_fitness(self, chromosome, current_station_id, next_station_id, delayed_trains):
        total_weighted_delay = 0.0
        adjusted_train_count = 0
        last_departure_mins = -999

        for train_idx in chromosome:
            train = delayed_trains[train_idx]
            weight = 0.3 if self._get_train_grade(train.train_number) >= 3 else 0.1
            curr_pt = next((p for p in train.points if p.station_id == current_station_id), None)
            next_pt = next((p for p in train.points if p.station_id == next_station_id), None)

            if not curr_pt or not next_pt: continue

            ready_to_dep_mins = self._time_to_mins(curr_pt.planned_departure)
            actual_dep_mins = max(ready_to_dep_mins, last_departure_mins + 3)
            last_departure_mins = actual_dep_mins

            run_time = self.section_times.get((current_station_id, next_station_id), 4)
            actual_arr_next_mins = actual_dep_mins + run_time
            planned_arr_next_mins = self._time_to_mins(next_pt.planned_arrival)

            delay = max(0, actual_arr_next_mins - planned_arr_next_mins)
            total_weighted_delay += delay * weight
            if delay > 0:
                adjusted_train_count += 1

        # ================= 多目标优化 =================
        # 目标1：使得加权晚点总时间尽量小
        # 目标2：使得晚点列车的数量尽量少
        W1 = 1.0  # 晚点时间的权重
        W2 = 50.0  # 晚点列车数的权重

        comprehensive_cost = (W1 * total_weighted_delay) + (W2 * adjusted_train_count)

        if comprehensive_cost == 0: return 99999.0
        return 1.0 / comprehensive_cost

    def _time_to_mins(self, qt):
        return qt.hour() * 60 + qt.minute() if qt else 0

    def _get_train_grade(self, train_num):
        prefix = str(train_num)[0].upper()
        if prefix == 'G': return 4
        if prefix == 'D': return 3
        if prefix == 'C': return 2
        return 1