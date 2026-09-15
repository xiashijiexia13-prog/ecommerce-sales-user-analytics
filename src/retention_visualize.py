# -*- coding: utf-8 -*-
"""
留存率热力图
=============
功能：读取 data/retention.csv，画成热力图（颜色深浅 = 留存率高低）
用法：在虚拟环境中运行  python src/retention_visualize.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')   # 不弹窗，直接存成图片文件
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 1. 读取留存率矩阵（retention_analysis.py 已算好保存）
retention = pd.read_csv('data/retention.csv', index_col=0)
print(f"读取留存率矩阵：{retention.shape[0]} 个首购月 × {retention.shape[1]} 个观察月")

# 2. 自定义蓝色渐变（浅 = 低留存，深 = 高留存）
#    NaN（还没到观察期）显示为白色空白
blue_cmap = LinearSegmentedColormap.from_list(
    'blue_seq', ['#cde2fb', '#86b6ef', '#3987e5', '#1c5cab', '#0d366b']
)
blue_cmap.set_bad('white')

fig, ax = plt.subplots(figsize=(11, 7))

# 3. 画热力图：vmin=0, vmax=100 让颜色和"0~100%"严格对应（不拉伸、不误导）
im = ax.imshow(retention.values, cmap=blue_cmap, vmin=0, vmax=100, aspect='auto')

# 4. 坐标轴：x = 第 N 月，y = 首购月
ax.set_xticks(range(retention.shape[1]))
ax.set_xticklabels(retention.columns, fontsize=10)
ax.set_yticks(range(retention.shape[0]))
ax.set_yticklabels(retention.index, fontsize=10)

# 5. 每个格子写数字（NaN 空白格不写）
for i in range(retention.shape[0]):
    for j in range(retention.shape[1]):
        val = retention.values[i, j]
        if np.isnan(val):
            continue
        # 深色格子配白字，浅色格子配黑字
        text_color = 'white' if val >= 60 else 'black'
        ax.text(j, i, f'{val:.1f}', ha='center', va='center',
                fontsize=9, color=text_color)

# 6. 颜色条 + 标题
cbar = plt.colorbar(im, ax=ax, shrink=0.85)
cbar.set_label('留存率（%）', fontsize=11)
ax.set_xlabel('距首购月数（第 N 月）', fontsize=12)
ax.set_ylabel('首购月', fontsize=12)
ax.set_title('新用户留存率热力图（颜色越深 = 留存率越高）', fontsize=14, pad=15)

plt.tight_layout()
os.makedirs('reports', exist_ok=True)
plt.savefig('reports/retention_heatmap.png', dpi=150, bbox_inches='tight')
print('留存热力图已保存到 reports/retention_heatmap.png')
