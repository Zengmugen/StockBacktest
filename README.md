# StockBacktest · A股策略回测工具

一款基于 **Python** 的 A 股**多策略**回测小工具,带图形界面。输入股票代码与参数,自动获取历史行情、回测策略,并给出绩效指标与资金曲线图。内置**双均线 / RSI / 布林带 / MACD** 四种策略。

> ⚠️ 免责声明:本工具仅用于历史数据的技术回测与学习研究,**不构成任何投资建议**。据此操作,风险自负。

## 功能

- **自动获取行情**:通过东方财富公开接口(仅需 `requests`)免费获取 A 股日线数据(也支持读取本地 CSV;另可切换到 `akshare`)
- **四种内置策略**(参数均可调):
  - 双均线 MA:短均线上穿长均线买入、下穿卖出
  - RSI 超买超卖:超卖买入、超买卖出
  - 布林带均值回归:跌破下轨买入、回到中轨卖出
  - MACD 金叉死叉:DIF 上穿 DEA 买入、下穿卖出
- **绩效指标**:总收益率、年化收益率、最大回撤、夏普比率、胜率、交易次数
- **基准对比**:与"买入并持有"对比,给出超额收益
- **可视化**:价格 + 买卖点标注图、策略资金曲线 vs 基准
- **图形界面**:tkinter GUI,不懂代码也能用;另提供命令行版
- **成本模型**:内置佣金、印花税、滑点,回测更贴近真实

## 环境与安装

```bash
pip install -r requirements.txt
```

需要 Python 3.9+。

## 使用

### 图形界面（推荐）

```bash
python gui.py
```

在顶部输入股票代码（如 `000001`）、日期区间、均线参数,点击「开始回测」。
无网络时可点「示例数据演示」,用内置的 `sample_data.csv` 跑一遍。

### 命令行

```bash
# 在线获取行情回测
python cli.py --symbol 000001 --start 20220101 --end 20240101 --short 5 --long 20

# 用本地 CSV 回测
python cli.py --csv sample_data.csv --short 10 --long 30
```

CSV 需包含 `date, open, high, low, close, volume` 列（中英文列名均可）。

## 项目结构

| 文件 | 说明 |
| --- | --- |
| `stock_backtest.py` | 核心:数据获取、策略信号、回测引擎、绩效指标 |
| `plotting.py` | 绘图:价格+买卖点、资金曲线 |
| `gui.py` | 图形界面 |
| `cli.py` | 命令行入口 |
| `sample_data.csv` | 示例行情数据（离线演示用） |

## 技术栈

Python · pandas · numpy · matplotlib · requests · tkinter

## License

MIT
