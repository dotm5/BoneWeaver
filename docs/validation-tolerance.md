# Validation Tolerance Contract

`AUTO_PRODUCTION` is the default. It compares evaluated Mesh object-local vertices and records world-space deltas only for diagnosis. Each Mesh owns its scale and limits; scene-wide dimensions never set another Mesh's tolerance.

Central defaults are `auto_relative_factor=2.5e-7`, `baseline_noise_multiplier=4`, `float32_ulp_multiplier=8`, and `hard_limit_multiplier=4`. The no-op baseline captures A, updates the dependency graph, and captures B without scene mutation. Float32 ULP uses `struct.pack/unpack` and adjacent representations.

Per Mesh the report includes scale, mode, soft/hard limits, baseline max/RMS, ULP budget, max/mean/RMS delta, soft/hard outliers, result, and recommended limits. `PASS_WITH_NUMERIC_NOISE_WARNING` requires maximum below hard, RMS below 25% of soft, and no more than `max(4, ceil(V*1e-6))` soft outliers. All other exceedances roll back.

`STRICT_TEST` retains the strict fixture behavior. `CUSTOM` uses `position_epsilon_factor`. Neither mode automatically retries Apply.
