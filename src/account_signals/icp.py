from __future__ import annotations

from dataclasses import dataclass

from account_signals.models import Account, Reason


@dataclass(frozen=True)
class IdealCustomerProfile:
    industries: frozenset[str]
    regions: frozenset[str]
    min_revenue_usd: int
    max_revenue_usd: int
    min_employees: int


DEFAULT_ICP = IdealCustomerProfile(
    industries=frozenset({"saas", "developer tools", "edtech", "productivity"}),
    regions=frozenset({"GB", "US", "CA", "DE", "NL", "FR", "IE", "SE"}),
    min_revenue_usd=2_000_000,
    max_revenue_usd=200_000_000,
    min_employees=20,
)


def fit_score(
    account: Account, icp: IdealCustomerProfile = DEFAULT_ICP
) -> tuple[float, list[Reason]]:
    reasons: list[Reason] = []
    if account.sells_software:
        reasons.append(Reason("sells_software", 35, "Sells software or digital products"))
    if account.industry.lower() in icp.industries:
        reasons.append(Reason("industry", 20, f"Industry '{account.industry}' is in the ICP"))
    if account.country in icp.regions:
        reasons.append(Reason("region", 15, f"Based in a core region ({account.country})"))
    if icp.min_revenue_usd <= account.annual_revenue_usd <= icp.max_revenue_usd:
        reasons.append(Reason("revenue", 20, "Revenue inside the target band"))
    if account.employees >= icp.min_employees:
        reasons.append(Reason("size", 10, f"{account.employees} employees"))
    return sum(reason.points for reason in reasons), reasons
