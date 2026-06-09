from pandera import Column, Check, DataFrameSchema

BatchInputSchema = DataFrameSchema(
    {
        "item_name": Column(str, nullable=False),
        "user_description": Column(str, nullable=True),
        "used_days": Column(int, Check.ge(0), coerce=True),
        "remaining_pct": Column(float, Check.in_range(0.0, 100.0), coerce=True),
        "weekly_use_count": Column(float, Check.ge(0.0), coerce=True),
        "user_count": Column(int, Check.ge(1), coerce=True),
        "is_shared": Column(int, Check.isin([0, 1]), coerce=True),
        "has_shelf_life": Column(int, Check.isin([0, 1]), coerce=True),
        "days_to_expire": Column(int, coerce=True),
        "is_damaged": Column(int, Check.isin([0, 1]), coerce=True),
    },
    coerce=True,
)
