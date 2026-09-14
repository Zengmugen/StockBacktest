# -*- coding: utf-8 -*-
"""命令行入口:一条命令跑完整回测并出图。

用法示例:
    python cli.py --symbol 000001 --start 20220101 --end 20240101
    python cli.py --symbol 600519 --strategy macd
    python cli.py --strategy rsi --params period=14,oversold=30,overbought=70 --symbol 000001
    python cli.py --csv sample_data.csv --strategy boll --params period=20,num_std=2
"""

import argparse
import datetime as dt

from stock_backtest import (
    BacktestConfig, STRATEGIES, load_data_akshare, load_data_csv,
    run_backtest, format_metrics,
)
from plotting import plot_result


def parse_params(spec_params, params_str):
    """把 'k=v,k=v' 解析成带类型的 kwargs,缺省用默认值。"""
    overrides = {}
    if params_str:
        for kv in params_str.split(","):
            k, _, v = kv.partition("=")
            overrides[k.strip()] = v.strip()
    kwargs = {}
    for pk, plabel, default, typ in spec_params:
        kwargs[pk] = typ(overrides[pk]) if pk in overrides else default
    return kwargs


def main():
    p = argparse.ArgumentParser(description="A 股多策略回测工具")
    p.add_argument("--symbol", help="6 位股票代码,如 000001")
    p.add_argument("--csv", help="本地行情 CSV 路径(与 --symbol 二选一)")
    p.add_argument("--start", default="20220101", help="开始日期 YYYYMMDD")
    p.add_argument("--end", default=dt.date.today().strftime("%Y%m%d"), help="结束日期 YYYYMMDD")
    p.add_argument("--strategy", default="ma", choices=list(STRATEGIES.keys()),
                   help="策略: ma / rsi / boll / macd")
    p.add_argument("--params", default="", help="策略参数,如 short=5,long=20")
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

    spec = STRATEGIES[args.strategy]
    kwargs = parse_params(spec["params"], args.params)
    pos = spec["func"](df, **kwargs)
    result = run_backtest(df, pos, BacktestConfig(initial_cash=args.cash))

    param_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    title = f"{name}  {spec['label']}({param_str})"
    print("\n" + "=" * 48)
    print(f" {title}")
    print(f" 区间: {df.index[0].date()} ~ {df.index[-1].date()}  共 {len(df)} 个交易日")
    print("=" * 48)
    print(format_metrics(result.metrics))
    print("=" * 48)

    out = plot_result(result, title, args.out)
    print(f"\n资金曲线图已保存: {out}")


if __name__ == "__main__":
    main()
