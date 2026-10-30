"""Clean the included raw snapshot without modifying source data."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import hashlib, json, sys, platform
import numpy as np
import pandas as pd

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=lambda x: x.item() if hasattr(x, 'item') else str(x)) + '\n')

def export(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format='%.6f', date_format='%Y-%m-%d', lineterminator='\n')

def profile(df):
    return [{'column': c, 'dtype': str(df[c].dtype), 'missing': int(df[c].isna().sum()), 'distinct': int(df[c].nunique(dropna=True))} for c in df]

def date_dimension(start, end):
    d = pd.DataFrame({'Date': pd.date_range(start, end, freq='D')})
    d['DateKey'] = d.Date.dt.strftime('%Y%m%d').astype(int)
    d['Year'] = d.Date.dt.year
    d['MonthNumber'] = d.Date.dt.month
    d['MonthName'] = d.Date.dt.strftime('%b')
    d['YearMonth'] = d.Date.dt.strftime('%Y-%m')
    d['YearMonthSort'] = d.Date.dt.year * 100 + d.Date.dt.month
    d['Weekday'] = d.Date.dt.day_name()
    d['WeekdayNumber'] = d.Date.dt.dayofweek + 1
    d['IsWeekend'] = (d.Date.dt.dayofweek >= 5).astype(int)
    return d

def seoul():
    p = ROOT
    raw = pd.read_csv(p / 'data/raw/SeoulBikeData.csv', encoding='cp1252')
    d = raw.rename(columns={'Date': 'Date', 'Rented Bike Count': 'Rentals', 'Hour': 'Hour', 'Temperature(°C)': 'TemperatureC', 'Humidity(%)': 'HumidityPct', 'Wind speed (m/s)': 'WindSpeedMps', 'Visibility (10m)': 'VisibilityUnits10m', 'Dew point temperature(°C)': 'DewPointC', 'Solar Radiation (MJ/m2)': 'SolarRadiationMJm2', 'Rainfall(mm)': 'RainfallMm', 'Snowfall (cm)': 'SnowfallCm', 'Seasons': 'Season', 'Holiday': 'Holiday', 'Functioning Day': 'FunctioningDay'}).copy()
    d['Date'] = pd.to_datetime(d.Date, format='%d/%m/%Y')
    d['DateKey'] = d.Date.dt.strftime('%Y%m%d').astype(int)
    d['Timestamp'] = d.Date + pd.to_timedelta(d.Hour, unit='h')
    d['SourceRow'] = np.arange(len(d)) + 2
    d['OperatingFlag'] = d.FunctioningDay.eq('Yes').astype(int)
    d['HolidayFlag'] = d.Holiday.eq('Holiday').astype(int)
    d['VisibilityMetres'] = d.VisibilityUnits10m * 10
    d['RainBand'] = np.where(d.RainfallMm.gt(0), 'Rain recorded', 'No rain')
    d['TemperatureBand'] = pd.cut(d.TemperatureC, [-np.inf, 0, 10, 20, 30, np.inf], labels=['Below 0°C', '0–10°C', '10–20°C', '20–30°C', 'Above 30°C']).astype(str)
    d['Daypart'] = pd.cut(d.Hour, [-1, 5, 9, 15, 19, 23], labels=['Overnight', 'Morning commute', 'Midday', 'Evening commute', 'Late evening']).astype(str)
    d['TemperatureBandOrder'] = d.TemperatureBand.map({'Below 0°C': 1, '0–10°C': 2, '10–20°C': 3, '20–30°C': 4, 'Above 30°C': 5})
    assert not d.Timestamp.duplicated().any() and len(d) == 8760 and d.Rentals.ge(0).all() and d.Hour.between(0, 23).all()
    assert d.loc[d.OperatingFlag.eq(0), 'Rentals'].eq(0).all()
    dates = date_dimension(d.Date.min(), d.Date.max())
    export(d.drop(columns=['Date', 'Timestamp', 'Holiday', 'FunctioningDay', 'VisibilityUnits10m']), p / 'data/clean/FactDemand.csv')
    export(dates, p / 'data/clean/DimDate.csv')
    hours = pd.DataFrame({'Hour': range(24)})
    hours['HourLabel'] = hours.Hour.map(lambda x: f'{x:02d}:00')
    hours['Daypart'] = pd.cut(hours.Hour, [-1, 5, 9, 15, 19, 23], labels=['Overnight', 'Morning commute', 'Midday', 'Evening commute', 'Late evening']).astype(str)
    export(hours, p / 'data/clean/DimHour.csv')
    export(pd.DataFrame({'Season': ['Winter', 'Spring', 'Summer', 'Autumn'], 'SeasonOrder': [1, 2, 3, 4]}), p / 'data/clean/DimSeason.csv')
    d['YearMonth'] = d.Date.dt.strftime('%Y-%m')
    d['Weekday'] = d.Date.dt.day_name()
    d['WeekdayNumber'] = d.Date.dt.dayofweek + 1
    for col in ['YearMonth', 'Season', 'Hour', 'Weekday', 'RainBand', 'TemperatureBand']:
        g = d.groupby(col, observed=True).agg(TotalRentals=('Rentals', 'sum'), RecordedHours=('Rentals', 'size'), OperatingHours=('OperatingFlag', 'sum'), AverageTemperatureC=('TemperatureC', 'mean')).reset_index()
        g['RentalsPerOperatingHour'] = g.TotalRentals / g.OperatingHours.replace(0, np.nan)
        if col == 'Weekday':
            g = g.merge(d[['Weekday', 'WeekdayNumber']].drop_duplicates(), on='Weekday').sort_values('WeekdayNumber')
        export(g, p / 'analysis' / f'{col}.csv')
    heat = d.loc[d.OperatingFlag.eq(1)].pivot_table(index='WeekdayNumber', columns='Hour', values='Rentals', aggfunc='mean')
    export(heat.reset_index(), p / 'analysis/hour_weekday.csv')
    summary = {'source_rows': len(raw), 'clean_rows': len(d), 'missing_cells_source': int(raw.isna().sum().sum()), 'exact_duplicates_source': int(raw.duplicated().sum()), 'total_rentals': int(d.Rentals.sum()), 'recorded_hours': len(d), 'operating_hours': int(d.OperatingFlag.sum()), 'non_operating_hours': int(d.OperatingFlag.eq(0).sum()), 'rentals_per_operating_hour': float(d.Rentals.sum() / d.OperatingFlag.sum()), 'peak_single_hour_rentals': int(d.Rentals.max()), 'start': d.Date.min().strftime('%Y-%m-%d'), 'end': d.Date.max().strftime('%Y-%m-%d'), 'cleaning_policy': 'Keep all 8,760 hourly records. Parse day-first dates; standardize unit-bearing headers; explicitly flag non-operating hours; convert visibility from 10-metre units to metres. No fabricated missingness or outlier deletion.', 'metric_scope': 'Rentals are observed counts, not fleet utilization, unmet demand, or available-bike capacity. Weather associations are descriptive and seasonally confounded.'}
    save_json(p / 'analysis/summary.json', summary)
    save_json(p / 'analysis/cleaning_audit.json', {'before': profile(raw), 'after': profile(d), 'rows_removed': 0, 'date_format': '%d/%m/%Y', 'visibility_conversion': 'source units × 10 = metres', 'non_operating_rows_retained': summary['non_operating_hours']})
    return summary

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    print(json.dumps(seoul(), indent=2, default=str))
