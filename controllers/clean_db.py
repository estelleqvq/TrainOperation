import pymysql
from config import DB_CONFIG

# 连接数据库并清空 plans 里的脏数据
conn = pymysql.connect(**DB_CONFIG)
with conn.cursor() as cursor:
    cursor.execute("TRUNCATE TABLE plans")
conn.commit()
conn.close()

print("数据库旧的冗余数据已全部清空！下次启动将重新加载一份干净的底稿。")