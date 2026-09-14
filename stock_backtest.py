# -*- coding: utf-8 -*-
"""
A 股策略回测工具 —— 核心引擎

功能:
  · 通过 akshare 自动获取 A 股历史行情(也支持读取本地 CSV)
  · 内置双均线(MA 金叉/死叉)策略,参数可调
  · 计算总收益、年化收益、最大回撤、夏普比率、胜率、交易次数等指标
  · 与"买入并持有"基准对比
  · 生成资金曲线图 + 买卖点标注图

免责声明:本工具仅用于历史数据的技术回测与学习研究,不构成任何投资建议。
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# 数据获取
# --------------------------------------------------------------------------- #
def load_data_akshare(symbol: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
    """用 akshare 获取 A 股日线数据。

    symbol : 6 位股票代码,如 "000001"、"600519"
    start  : 开始日期 "YYYYMMDD"
    end    : 结束日期 "YYYYMMDD"
    adjust : 复权方式 "qfq"(前复权)/"hfq"(后复权)/""(不复权)
    返回列: date, open, high, low, close, volume(date 为索引)
    """
    import time
    import akshare as ak

    last_err = None
    df = None
    for attempt in range(3):  # 行情接口偶发抖动,自动重试
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol, period="daily", start_date=start, end_date=end, adjust=adjust
            )
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5)
    if df is None:
        raise ConnectionError(
            f"获取 {symbol} 行情失败,请检查网络后重试。原因: {last_err}"
        )
    if df.empty:
        raise ValueError(f"未获取到 {symbol} 在 {start}~{end} 的数据,请检查代码或日期。")

    df = df.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        }
    )
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def load_data_csv(path: str) -> pd.DataFrame:
    """从本地 CSV 读取行情。需包含 date/open/high/low/close/volume 列(中英文均可)。"""
    df = pd.read_csv(path)
    rename = {
        "日期": "date", "开盘": "open", "最高": "high",
        "最低": "low", "收盘": "close", "成交量": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    need = ["date", "open", "high", "low", "close", "volume"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少必要列: {missing}")
    df["date"] = pd.to_datetime(df["date"])
    return df[need].set_index("date").sort_index()


# --------------------------------------------------------------------------- #
# 策略:双均线金叉/死叉
# --------------------------------------------------------------------------- #
def signal_ma_cross(df: pd.DataFrame, short: int = 5, long: int = 20) -> pd.Series:
    """短均线上穿长均线 -> 持仓(1);下穿 -> 空仓(0)。

    返回每日目标仓位 Series(0 或 1),已右移一天以避免使用未来信息
    (今天收盘产生的信号,明天才建/平仓)。
    """
    if short >= long:
        raise ValueError("短周期必须小于长周期。")
    ma_s = df["close"].rolling(short).mean()
    ma_l = df["close"].rolling(long).mean()
    pos = (ma_s > ma_l).astype(int)
    pos = pos.shift(1).fillna(0)  # 次日执行,避免前视偏差
    return pos


# --------------------------------------------------------------------------- #
# 回测引擎
# --------------------------------------------------------------------------- #
@dataclass
class BacktestConfig:
    initial_cash: float = 100_000.0   # 初始资金
    commission: float = 0.0003        # 单边佣金费率(万三)
    stamp_tax: float = 0.0005         # 印花税(卖出时收取)
    slippage: float = 0.0             # 滑点(按比例)


@dataclass
class BacktestResult:
    equity: pd.Series                 # 策略资金曲线
    benchmark: pd.Series              # 买入持有资金曲线
    trades: list = field(default_factory=list)  # 成交明细
    metrics: dict = field(default_factory=dict) # 绩效指标
    data: pd.DataFrame = None         # 行情 + 仓位


def run_backtest(df: pd.DataFrame, position: pd.Series, cfg: BacktestConfig) -> BacktestResult:
    """按每日目标仓位(0/1)进行全仓买卖的向量化回测。"""
    df = df.copy()
    df["position"] = position.reindex(df.index).fillna(0).astype(int)

    close = df["close"].values
    pos = df["position"].values
    n = len(df)

    cash = cfg.initial_cash
    shares = 0.0
    equity = np.zeros(n)
    trades = []
    prev_pos = 0

    for i in range(n):
        price = close[i]
        # 仓位变化 -> 交易
        if pos[i] == 1 and prev_pos == 0:               # 买入(全仓)
            buy_price = price * (1 + cfg.slippage)
            shares = cash / (buy_price * (1 + cfg.commission))
            cost = shares * buy_price * (1 + cfg.commission)
            cash -= cost
            trades.append({"date": df.index[i], "type": "买入", "price": buy_price, "shares": shares})
        elif pos[i] == 0 and prev_pos == 1:             # 卖出(清仓)
            sell_price = price * (1 - cfg.slippage)
            proceeds = shares * sell_price * (1 - cfg.commission - cfg.stamp_tax)
            cash += proceeds
            entry = trades[-1]["price"]
            trades.append({
                "date": df.index[i], "type": "卖出", "price": sell_price,
                "shares": shares, "return": sell_price / entry - 1,
            })
            shares = 0.0
        equity[i] = cash + shares * price
        prev_pos = pos[i]

    df["equity"] = equity
    equity_s = pd.Series(equity, index=df.index)

    # 基准:期初全仓买入并持有
    bench = cfg.initial_cash * (close / close[0])
    bench_s = pd.Series(bench, index=df.index)

    metrics = _calc_metrics(equity_s, bench_s, trades, df)
    return BacktestResult(equity=equity_s, benchmark=bench_s, trades=trades,
                          metrics=metrics, data=df)


def _calc_metrics(equity: pd.Series, bench: pd.Series, trades: list, df: pd.DataFrame) -> dict:
    ret = equity.iloc[-1] / equity.iloc[0] - 1
    days = (equity.index[-1] - equity.index[0]).days or 1
    years = days / 365.0
    ann = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0

    # 最大回撤
    roll_max = equity.cummax()
    drawdown = equity / roll_max - 1
    max_dd = drawdown.min()

    # 夏普(按日收益,年化)
    daily = equity.pct_change().dropna()
    sharpe = (daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0.0

    # 交易统计(按卖出算一次完整交易)
    sells = [t for t in trades if t["type"] == "卖出"]
    n_trades = len(sells)
    wins = [t for t in sells if t.get("return", 0) > 0]
    win_rate = len(wins) / n_trades if n_trades else 0.0

    bench_ret = bench.iloc[-1] / bench.iloc[0] - 1

    return {
        "总收益率": ret,
        "年化收益率": ann,
        "最大回撤": max_dd,
        "夏普比率": sharpe,
        "交易次数": n_trades,
        "胜率": win_rate,
        "基准收益率(买入持有)": bench_ret,
        "超额收益": ret - bench_ret,
    }


_PERCENT_KEYS = {
    "总收益率", "年化收益率", "最大回撤", "胜率",
    "基准收益率(买入持有)", "超额收益",
}


def format_metrics(metrics: dict) -> str:
    """把指标字典格式化成易读文本。"""
    lines = []
    for k, v in metrics.items():
        if k == "交易次数":
            lines.append(f"{k:<18}: {int(v)}")
        elif k in _PERCENT_KEYS:
            lines.append(f"{k:<18}: {v * 100:>7.2f} %")
        else:  # 夏普比率等纯数值
            lines.append(f"{k:<18}: {v:>7.2f}")
    return "\n".join(lines)
