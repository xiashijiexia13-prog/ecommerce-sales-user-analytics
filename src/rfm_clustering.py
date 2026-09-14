# -*- coding: utf-8 -*-
"""
RFM 用户分层分析（第二步：标准化 + KMeans 聚类）
=================================================
功能：读取第一步算好的 data/rfm.csv，标准化后用 KMeans 把用户聚类分层
用法：在虚拟环境中运行  python src/rfm_clustering.py

关键点：
  1. 标准化：R/F/M 量纲不同（R~百、F~个位、M~万），
     不标准化会让 M 主导距离计算，必须先缩放到同一量级
  2. 肘部法：尝试不同 K，看 SSE 下降趋势，选"拐点"作为聚类数
  3. KMeans：无监督学习，自动把"特征接近"的用户归为一类
"""

import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')   # 不弹窗，直接把图存成文件
import matplotlib.pyplot as plt

# 设置中文字体（matplotlib 默认字体不含中文，会显示成乱码/方块）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 优先黑体，其次微软雅黑
plt.rcParams['axes.unicode_minus'] = False   # 解决负号(-)也显示成方块的问题

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# 1. 读取第一步算好的 RFM 数据
rfm = pd.read_csv('data/rfm.csv')
print(f"读取 RFM 数据：{len(rfm)} 个用户")

# 2. 标准化：把 R/F/M 都变成"均值 0、标准差 1"的分布
scaler = StandardScaler()
rfm_scaled = scaler.fit_transform(rfm[['R', 'F', 'M']])

print("\n标准化前（三个指标量级差异巨大）：")
print(rfm[['R', 'F', 'M']].describe().round(2).to_string())

print("\n标准化后（三个指标量级统一了）：")
print(pd.DataFrame(rfm_scaled, columns=['R', 'F', 'M']).describe().round(2).to_string())

# 3. 肘部法：尝试 K=2~10，看"簇内误差平方和(SSE)"的下降趋势
#    SSE 越小 = 每个簇内部越紧凑；但当 K 太大时，收益递减，找"拐点"
print("\n肘部法：不同 K 值下的 SSE")
sse = []
K_range = range(2, 11)
for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(rfm_scaled)
    sse.append(km.inertia_)
    print(f"  K={k:>2}  SSE={km.inertia_:.2f}")

# 画肘部曲线
plt.figure(figsize=(8, 5))
plt.plot(list(K_range), sse, marker='o')
plt.xlabel('聚类数 K')
plt.ylabel('SSE（簇内误差平方和）')
plt.title('肘部法：选择合适的 K')
plt.grid(True, linestyle='--', alpha=0.5)
os.makedirs('reports', exist_ok=True)
plt.savefig('reports/elbow.png', dpi=150)
print("\n肘部曲线已保存到 reports/elbow.png（可打开看图找拐点）")

# 4. 用 K=4 跑 KMeans（RFM 常见分段数，看完肘部图可以调整 K 再跑一次）
K = 4
km = KMeans(n_clusters=K, random_state=42, n_init=10)
rfm['cluster'] = km.fit_predict(rfm_scaled)

# 5. 关键：把聚类中心从"标准化空间"还原回"原始量纲"，否则看不懂
#    inverse_transform 把"均值0标准差1"的坐标换算回"天数/次数/元"
centers = scaler.inverse_transform(km.cluster_centers_)
centers_df = pd.DataFrame(centers, columns=['R', 'F', 'M'])
centers_df['用户数'] = rfm['cluster'].value_counts().sort_index().values
centers_df.index.name = 'cluster'

print(f"\n===== K={K} 的聚类结果（每类用户的平均 R/F/M） =====")
print(centers_df.round(1).to_string())

# 6. 保存带聚类标签的结果，供下一步画图和贴业务标签使用
rfm.to_csv('data/rfm_clustered.csv', index=False)
print(f"\n聚类结果已保存到 data/rfm_clustered.csv")
