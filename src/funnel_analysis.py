# -*- coding: utf-8 -*-
"""
漏斗分析可视化：下单 → 支付 → 完成
====================================
功能：把 SQL 算好的三个漏斗数字，画成横向漏斗图
用法：在虚拟环境中运行  python src/funnel_analysis.py

分工说明：数字由 SQL 在 Navicat 里算出（下单 55000 → 支付 46150 → 完成 43504），
          这里 Python 只负责"画图"。这正是 SQL 算、Python 画 的分工。
"""

import matplotlib
matplotlib.use('Agg')   # 不弹窗，直接存成图片文件
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 1. 漏斗数据（= Navicat 里 SQL 算出的结果）
stages = ['下单', '支付', '完成']
values = [55000, 46150, 43504]
# 统一蓝色系，从浅到深表示"越深入漏斗"（不是默认的随机颜色）
colors = ['#86b6ef', '#3987e5', '#184f95']

fig, ax = plt.subplots(figsize=(10, 5))

# 2. 画横向条形，下单在最上面
#    np.arange(3)[::-1] = [2,1,0]，让"下单"排在最上面
y = np.arange(len(stages))[::-1]
ax.barh(y, values, color=colors, height=0.55)

# 3. 柱尾标数量（f'{v:,}' 会显示成千分位 55,000）
for yi, v in zip(y, values):
    ax.text(v + 1200, yi, f'{v:,} 单', va='center', ha='left',
            fontsize=12, color='#0b0b0b')

# 4. 左轴标阶段名
ax.set_yticks(y)
ax.set_yticklabels(stages, fontsize=13)

# 5. 两步转化率，标在相邻两柱中间的空隙
#    白色小标签盖在柱子上也能看清楚
for gy, label in [(1.5, '下单→支付  83.91%'), (0.5, '支付→完成  94.27%')]:
    ax.text(2000, gy, label, va='center', ha='left', fontsize=10, color='#52514e',
            bbox=dict(facecolor='white', edgecolor='#e1e0d9', boxstyle='round,pad=0.35'))

# 6. 美化：隐藏 x 轴刻度与上/下/右边框（数量已经标在柱尾了）
ax.set_xlim(0, max(values) * 1.18)
ax.set_xticks([])
for s in ('top', 'right', 'bottom'):
    ax.spines[s].set_visible(False)
ax.set_title('下单 → 支付 → 完成 转化漏斗', fontsize=14, pad=18)

plt.tight_layout()
plt.savefig('reports/funnel.png', dpi=150, bbox_inches='tight')
print('漏斗图已保存到 reports/funnel.png')
