from findings.rules import (
    BaseFindingRule,
    IdleComputeRule,
    MissingTagsRule,
    ObservabilityGapRule,
    PublicExposureRule,
    UnattachedVolumeRule,
)


class FindingRuleRegistry:
    def __init__(self) -> None:
        self._rules: list[BaseFindingRule] = [
            MissingTagsRule(),
            PublicExposureRule(),
            UnattachedVolumeRule(),
            IdleComputeRule(),
            ObservabilityGapRule(),
        ]

    def rules(self) -> list[BaseFindingRule]:
        return list(self._rules)
