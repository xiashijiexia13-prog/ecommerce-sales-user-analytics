# -*- coding: utf-8 -*-
"""
数据质量检查（Python / pandas 版）
==================================
功能：从 MySQL 读取数据，用 pandas 按"数据质量6维度"做检查
用法：在虚拟环境中运行  python src/quality_check.py
说明：本脚本只"检查"不"修改"，清洗在 src/data_clean.py 里做
"""

import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine

# 1. 连接数据库，读取数据
load_dotenv(dotenv_path='.env')
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
)

orders = pd.read_sql("SELECT * FROM orders", engine)   # 订单表
users = pd.read_sql("SELECT * FROM users", engine)     # 用户表

print("========== 数据质量检查（Python / pandas 版） ==========\n")

# 2. 完整性检查：缺失值（isnull() 判断是否为空，sum() 数个数）
print("[完整性] 缺失值统计：")
print("  订单表 region 缺失   :", orders['region'].isnull().sum())
print("  订单表 channel 缺失  :", orders['channel'].isnull().sum())
print("  订单表 pay_time 缺失 :", orders['pay_time'].isnull().sum())

# 3. 唯一性检查：重复订单号（duplicated() 标记"是否重复出现"）
dup_count = orders['order_id'].duplicated().sum()
print("\n[唯一性] 重复订单号（order_id 重复出现）:", dup_count)

# 4. 准确性检查：异常金额（负数/0/极端值，用 | 表示"或"）
abnormal_amount = orders[(orders['amount'] < 0) | (orders['amount'] == 0) | (orders['amount'] > 50000)]
print("[准确性] 异常金额订单数:", len(abnormal_amount))

# 5. 一致性检查：支付时间早于下单时间
time_error = orders[orders['pay_time'] < orders['order_time']]
print("[一致性] 支付时间早于下单时间:", len(time_error))

# 6. 一致性检查：已支付但支付时间为空（用 & 表示"且"）
status_error = orders[(orders['status'] == '已支付') & (orders['pay_time'].isnull())]
print("[一致性] 已支付但支付时间为空:", len(status_error))

# 7. 有效性检查：年龄异常（0 或 200）
abnormal_age = users[(users['age'] == 0) | (users['age'] == 200)]
print("\n[有效性] 年龄异常用户数:", len(abnormal_age))

print("\n========== 检查完成 ==========")
print("注意：以上只是'发现问题'，下一步 data_clean.py 负责'解决问题'（清洗）")
