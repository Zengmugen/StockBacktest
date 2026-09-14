# -*- coding: utf-8 -*-
"""命令行入口:一条命令跑完整回测并出图。

用法示例:
    python cli.py --symbol 000001 --start 20220101 --end 20240101 --short 5 --long 20
    python cli.py --csv mydata.csv --short 10 --long 30
"""

import argparse
import datetime as dt

from stock_backtest import (
    BacktestConfig, load_data_akshare, load_data_csv,
    signal_ma_cross, run_backtest, format_metrics,
)
from plotting import plot_result


def main():
    p = argparse.ArgumentParser(description="A 股双均线策略回测工具")
    p.add_argument("--symbol", help="6 位股票代码,如 000001")
    p.add_argument("--csv", help="本地行情 CSV 路径(与 --symbol 二选一)")
    p.add_argument("--start", default="20220101", help="开始日期 YYYYMMDD")
    p.add_argument("--end", default=dt.date.today().strftime("%Y%m%d"), help="结束日期 YYYYMMDD")
    p.add_argument("--short", type=int, default=5, help="短均线周期")
    p.add_argument("--long", type=int, default=20, help="长均线周期")
    p.add_argument("--cash", type=float, default=100000, help="初始资金")
    p.add_argument("--out", default="backtest_result.png", help="输出图片路径")
    args = p.parse_args()

    if args.csv:
        df = load_data_csv(args.csv)
        name = args.csv
    elif args.symbol:
        print(f"正在获取 {args.symbol} 的行情数据 ...")
        df = load_data_akshare(args.symbol, args.start, args.end)
        name = args.symbol
    else:
        p.error("请提供 --symbol 或 --csv")

    pos = signal_ma_cross(df, args.short, args.long)
    cfg = BacktestConfig(initial_cash=args.cash)
    result = run_backtest(df, pos, cfg)

    title = f"{name}  双均线({args.short}/{args.long})回测"
    print("\n" + "=" * 44)
    print(f" {title}")
    print(f" 区间: {df.index[0].date()} ~ {df.index[-1].date()}  共 {len(df)} 个交易日")
    print("=" * 44)
    print(format_metrics(result.metrics))
    print("=" * 44)

    out = plot_result(result, title, args.out)
    print(f"\n资金曲线图已保存: {out}")


if __name__ == "__main__":
    main()
