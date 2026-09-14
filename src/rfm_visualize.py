# -*- coding: utf-8 -*-
"""
RFM 聚类可视化（第三步：把四类用户画出来）
============================================
功能：读取 data/rfm_clustered.csv，画两张散点图，用颜色区分四类用户
用法：在虚拟环境中运行  python src/rfm_visualize.py

为什么画图：表格里的数字太抽象，散点图能一眼看出四类人"各占一块地盘"，
            汇报/面试时"一张图顶十句话"。
为什么两张图：R/F/M 是三个维度，平面图只能画两个轴，
            所以左图画 F×M、右图画 R×M，把三个指标都覆盖到。
为什么 M 用对数坐标：消费金额跨度太大（几块钱到几十万），
            普通坐标会让小用户全挤在左下角，对数坐标能把量级拉开。
"""

import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')   # 不弹窗，直接存成图片文件
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# 设置中文字体（否则中文显示成乱码）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 对数坐标默认用 "10⁻¹、10²" 这种科学计数法刻度，
# 里面的负号(⁻)在 SimHei 字体里缺字形，会显示成方框。
# 这里改成普通数字刻度（0.1、10、10000…），既避开缺字也更直观。
money_formatter = FuncFormatter(lambda x, _pos: f"{x:g}")

# 1. 读取聚类结果
rfm = pd.read_csv('data/rfm_clustered.csv')
print(f"读取聚类结果：{len(rfm)} 个用户")

# 2. 把聚类编号(0/1/2/3)翻译成业务名字，图例才看得懂
cluster_names = {0: '活跃用户', 1: '普通用户', 2: '流失用户', 3: '高价值用户'}
rfm['客户类型'] = rfm['cluster'].map(cluster_names)

print("\n每类人数：")
print(rfm['客户类型'].value_counts().to_string())

# 3. 画图：一行两列
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 左图：购买次数 F × 消费金额 M
ax = axes[0]
for name in cluster_names.values():
    sub = rfm[rfm['客户类型'] == name]
    ax.scatter(sub['F'], sub['M'], s=8, alpha=0.6, label=name)
ax.set_xlabel('购买次数 F')
ax.set_ylabel('消费金额 M（元，对数坐标）')
ax.set_title('左图：买得多不多 × 花得多不多')
ax.set_yscale('log')   # M 跨度大，用对数坐标
ax.yaxis.set_major_formatter(money_formatter)   # 刻度改用普通数字，避开缺字
ax.legend(markerscale=3)
ax.grid(True, linestyle='--', alpha=0.4)

# 右图：距今天数 R × 消费金额 M
ax = axes[1]
for name in cluster_names.values():
    sub = rfm[rfm['客户类型'] == name]
    ax.scatter(sub['R'], sub['M'], s=8, alpha=0.6, label=name)
ax.set_xlabel('距今天数 R（天）')
ax.set_ylabel('消费金额 M（元，对数坐标）')
ax.set_title('右图：多久没来 × 花得多不多')
ax.set_yscale('log')
ax.yaxis.set_major_formatter(money_formatter)   # 刻度改用普通数字，避开缺字
ax.legend(markerscale=3)
ax.grid(True, linestyle='--', alpha=0.4)

# 4. 保存图片
plt.tight_layout()
os.makedirs('reports', exist_ok=True)
plt.savefig('reports/rfm_clusters.png', dpi=150)
print("\n聚类图已保存到 reports/rfm_clusters.png（打开看看四类人怎么分布）")
