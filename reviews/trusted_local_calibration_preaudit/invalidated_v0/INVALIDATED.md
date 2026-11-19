# Invalidated pre-audit implementation

The initial pilot incorrectly used received sender estimate minus the receiving Yang estimate, instead of the trusted local reference in the user request. Its covariance and all numeric results therefore concern the wrong residual. Preserved for audit, NOT evidence for the proposed method. The corrected version reuses identical seeds, bias, noise schedule, and window; no performance tuning.
