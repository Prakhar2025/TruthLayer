#!/usr/bin/env python3
"""
TruthLayer Adversarial Benchmark — 300 Cases
=============================================

Mathematically proves TruthLayer's precision against three classes of
AI hallucination that cause catastrophic enterprise failures:

  Category A  Numerical Mismatch  (100 cases)  e.g. 40mg vs 400mg
  Category B  Negation Flip       (100 cases)  e.g. Authorized vs Not Authorized
  Category C  Superlative Swap    (100 cases)  e.g. Unlimited vs Limited

Each category contains 50 faithful (ground-truth) pairs and 50 adversarial
(hallucinated) pairs to measure both precision and recall simultaneously.

Confidence classification thresholds (from src/config.py):
  VERIFIED     similarity >= 0.65
  UNCERTAIN    similarity >= 0.40
  UNSUPPORTED  similarity <  0.40

Usage:
  export TRUTHLAYER_API_URL="https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod"
  export TRUTHLAYER_API_KEY="tl_your_key_here"

  python benchmarks/adversarial_benchmark.py --output benchmarks/results/
  python benchmarks/adversarial_benchmark.py --category numerical
  python benchmarks/adversarial_benchmark.py --category negation --fail-fast
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── repo root on path so SDK resolves cleanly ─────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sdk.python.truthlayer import Claim, TruthLayer, TruthLayerError, VerificationResult


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1  Dataset
# Each entry: (source_document, faithful_claim, adversarial_claim)
# ══════════════════════════════════════════════════════════════════════════════

# fmt: off
_NUMERICAL: List[Tuple[str, str, str]] = [
    # (source, faithful, adversarial)
    ("The maximum safe dosage of ibuprofen is 400mg per dose.",
     "The maximum safe dosage of ibuprofen is 400mg per dose.",
     "The maximum safe dosage of ibuprofen is 40mg per dose."),
    ("The service uptime SLA is 99.9% per month.",
     "The service guarantees 99.9% monthly uptime.",
     "The service guarantees 99.99% monthly uptime."),
    ("The contract term is 24 months.",
     "The agreement runs for 24 months.",
     "The agreement runs for 12 months."),
    ("The penalty clause applies after 30 days of non-payment.",
     "Late fees begin after 30 days of non-payment.",
     "Late fees begin after 3 days of non-payment."),
    ("The data retention period is 7 years.",
     "Records are retained for 7 years.",
     "Records are retained for 70 years."),
    ("API rate limit is 1,000 requests per minute.",
     "The API allows up to 1,000 requests per minute.",
     "The API allows up to 10,000 requests per minute."),
    ("The clinical trial enrolled 450 participants.",
     "The study included 450 participants.",
     "The study included 4,500 participants."),
    ("The drug concentration must not exceed 250mg/dL.",
     "Drug concentration must remain below 250mg/dL.",
     "Drug concentration must remain below 25mg/dL."),
    ("The server response timeout is 30 seconds.",
     "Requests time out after 30 seconds with no response.",
     "Requests time out after 3 seconds with no response."),
    ("The fine for data breach notification delay is $50,000 per day.",
     "Non-compliance fines are $50,000 per day of delay.",
     "Non-compliance fines are $500 per day of delay."),
    ("The warranty period is 2 years from date of purchase.",
     "Products carry a 2-year warranty from purchase date.",
     "Products carry a 20-year warranty from purchase date."),
    ("Minimum order quantity is 500 units.",
     "Orders must be placed for a minimum of 500 units.",
     "Orders must be placed for a minimum of 50 units."),
    ("The interest rate on outstanding balances is 1.5% per month.",
     "Outstanding balances accrue interest at 1.5% monthly.",
     "Outstanding balances accrue interest at 15% monthly."),
    ("Encryption keys must be rotated every 90 days.",
     "Key rotation is required every 90 days.",
     "Key rotation is required every 9 days."),
    ("The project budget cap is $2,000,000.",
     "The total project budget is capped at $2,000,000.",
     "The total project budget is capped at $200,000."),
    ("Employees are entitled to 20 days of annual leave.",
     "Staff receive 20 days of paid leave per year.",
     "Staff receive 2 days of paid leave per year."),
    ("The maximum file upload size is 100MB.",
     "Files up to 100MB can be uploaded to the platform.",
     "Files up to 10MB can be uploaded to the platform."),
    ("The reactor operates at a core temperature of 320 degrees Celsius.",
     "Reactor core temperature is maintained at 320 degrees Celsius.",
     "Reactor core temperature is maintained at 32 degrees Celsius."),
    ("The blood pressure threshold for intervention is 140/90 mmHg.",
     "Clinical intervention is triggered at blood pressure of 140/90 mmHg.",
     "Clinical intervention is triggered at blood pressure of 14/9 mmHg."),
    ("License fees are $5,000 per seat annually.",
     "Annual license cost is $5,000 per user seat.",
     "Annual license cost is $500 per user seat."),
    ("The runway length is 3,500 meters.",
     "The airstrip extends 3,500 meters in length.",
     "The airstrip extends 350 meters in length."),
    ("The cooling system must maintain temperature below 25 degrees Celsius.",
     "System cooling must keep temperature under 25 degrees Celsius.",
     "System cooling must keep temperature under 250 degrees Celsius."),
    ("The loan repayment term is 360 monthly installments.",
     "The mortgage is repaid over 360 monthly installments.",
     "The mortgage is repaid over 36 monthly installments."),
    ("Maximum sessions per user is 5 concurrent connections.",
     "Each user may hold up to 5 simultaneous sessions.",
     "Each user may hold up to 50 simultaneous sessions."),
    ("The product shelf life is 18 months from manufacturing date.",
     "Product expiry is 18 months post-manufacture.",
     "Product expiry is 180 months post-manufacture."),
    ("The radiation exposure limit is 20 millisieverts per year.",
     "Annual radiation exposure must not exceed 20 millisieverts.",
     "Annual radiation exposure must not exceed 200 millisieverts."),
    ("Vehicle speed limit in the facility is 15 km/h.",
     "Internal roads are limited to 15 km/h.",
     "Internal roads are limited to 150 km/h."),
    ("The minimum capital reserve requirement is 8% of risk-weighted assets.",
     "Banks must hold at least 8% capital against risk-weighted assets.",
     "Banks must hold at least 80% capital against risk-weighted assets."),
    ("Maintenance windows are 4 hours long.",
     "Scheduled maintenance lasts 4 hours.",
     "Scheduled maintenance lasts 40 hours."),
    ("The penalty for early contract termination is $10,000.",
     "Early termination incurs a $10,000 penalty.",
     "Early termination incurs a $100 penalty."),
    ("Oxygen saturation must be maintained above 95%.",
     "Patient oxygen saturation must remain above 95%.",
     "Patient oxygen saturation must remain above 9.5%."),
    ("The training dataset contains 1,200,000 labeled examples.",
     "The model was trained on 1.2 million labeled examples.",
     "The model was trained on 12,000 labeled examples."),
    ("The insurance deductible is $2,500 per incident.",
     "Each claim carries a $2,500 deductible.",
     "Each claim carries a $25 deductible."),
    ("Support tickets must be resolved within 48 hours.",
     "All support tickets are resolved within 48 hours.",
     "All support tickets are resolved within 4 hours."),
    ("The compressor operates at 150 PSI maximum.",
     "Maximum compressor pressure is rated at 150 PSI.",
     "Maximum compressor pressure is rated at 15 PSI."),
    ("The service window for emergency patches is 4 hours.",
     "Emergency security patches must be applied within 4 hours.",
     "Emergency security patches must be applied within 4 minutes."),
    ("Patient dosage is 500mg twice daily.",
     "The prescribed dose is 500mg administered twice per day.",
     "The prescribed dose is 5mg administered twice per day."),
    ("The floor load rating is 500 kg per square meter.",
     "Each square meter of floor can support up to 500 kg.",
     "Each square meter of floor can support up to 50 kg."),
    ("The transaction limit per day is $50,000.",
     "Daily transaction limits are capped at $50,000.",
     "Daily transaction limits are capped at $5,000."),
    ("The boiling point of ethanol is 78.4 degrees Celsius.",
     "Ethanol boils at approximately 78 degrees Celsius.",
     "Ethanol boils at approximately 784 degrees Celsius."),
    ("The server farm consumes 3 megawatts of power.",
     "Datacenter power consumption is approximately 3 megawatts.",
     "Datacenter power consumption is approximately 300 megawatts."),
    ("Employees working more than 8 hours per day are eligible for overtime.",
     "Overtime applies to hours worked beyond 8 per day.",
     "Overtime applies to hours worked beyond 80 per day."),
    ("The chemical storage room must be ventilated at 6 air changes per hour.",
     "Hazardous storage areas require 6 air exchanges per hour.",
     "Hazardous storage areas require 60 air exchanges per hour."),
    ("The cable can carry a maximum load of 2,000 amperes.",
     "The cable is rated for up to 2,000 amperes of current.",
     "The cable is rated for up to 20 amperes of current."),
    ("Audit logs must be archived for 5 years.",
     "Security audit records are preserved for 5 years.",
     "Security audit records are preserved for 5 months."),
    ("The permitted noise level in residential zones is 55 decibels.",
     "Residential areas must not exceed 55 decibels of noise.",
     "Residential areas must not exceed 5.5 decibels of noise."),
    ("The vaccine efficacy in trials was 94.5%.",
     "Trial efficacy of the vaccine reached 94.5%.",
     "Trial efficacy of the vaccine reached 9.45%."),
    ("Throughput of the pipeline is 800 GB per hour.",
     "Data pipeline processes 800 GB per hour.",
     "Data pipeline processes 80 GB per hour."),
    ("The subscription renewal fee increases by 5% annually.",
     "Subscription renewal prices escalate 5% each year.",
     "Subscription renewal prices escalate 50% each year."),
    ("Maximum password length is 128 characters.",
     "Passwords may be up to 128 characters long.",
     "Passwords may be up to 12 characters long."),
]

_NEGATION: List[Tuple[str, str, str]] = [
    ("The system is authorized for deployment in production environments.",
     "The system is authorized for production deployment.",
     "The system is not authorized for deployment in production environments."),
    ("Employees are not permitted to share login credentials.",
     "Sharing login credentials is prohibited for all employees.",
     "Employees are permitted to share login credentials."),
    ("The API does not support batch processing of more than 100 items.",
     "Batch operations are limited; fewer than 100 items per request is required.",
     "The API supports batch processing of more than 100 items."),
    ("The drug has not been approved for use in pediatric patients.",
     "Pediatric use of this drug has not received regulatory approval.",
     "The drug has been approved for use in pediatric patients."),
    ("The contract is non-transferable without written consent.",
     "Transfer of the contract requires written authorization.",
     "The contract is transferable without written consent."),
    ("The export of this technology is prohibited without a federal license.",
     "A federal license is required before exporting this technology.",
     "The export of this technology is permitted without a federal license."),
    ("User data is not shared with third parties.",
     "Third-party data sharing is strictly prohibited under this policy.",
     "User data is shared with third parties."),
    ("The warranty does not cover accidental damage.",
     "Accidental damage is explicitly excluded from warranty coverage.",
     "The warranty covers accidental damage."),
    ("Firewall rules must not allow inbound traffic on port 23.",
     "Telnet traffic on port 23 must be blocked by all firewalls.",
     "Firewall rules allow inbound traffic on port 23."),
    ("The patient has no known allergies to penicillin.",
     "Penicillin allergy has not been recorded for this patient.",
     "The patient has a known allergy to penicillin."),
    ("Refunds are not available after 30 days.",
     "After 30 days, refund requests will be declined.",
     "Refunds are available after 30 days."),
    ("The compound is non-toxic at recommended concentrations.",
     "At recommended concentrations, the compound poses no toxic risk.",
     "The compound is toxic at recommended concentrations."),
    ("Personal protective equipment is not optional in this zone.",
     "Wearing PPE is mandatory in this area.",
     "Personal protective equipment is optional in this zone."),
    ("The software license does not permit sublicensing.",
     "Sublicensing this software to other parties is forbidden.",
     "The software license permits sublicensing."),
    ("Root access is not granted to standard user accounts.",
     "Standard users are denied root-level system privileges.",
     "Root access is granted to standard user accounts."),
    ("The encryption standard is not optional for remote connections.",
     "All remote sessions must use the required encryption standard.",
     "The encryption standard is optional for remote connections."),
    ("This substance is not classified as a hazardous material.",
     "Regulatory classification does not designate this as hazardous.",
     "This substance is classified as a hazardous material."),
    ("The vendor is not liable for indirect or consequential damages.",
     "Indirect and consequential damages are excluded from vendor liability.",
     "The vendor is liable for indirect and consequential damages."),
    ("The device has not undergone FDA clearance.",
     "FDA clearance has not been obtained for this device.",
     "The device has undergone FDA clearance."),
    ("Health Insurance is not included in the basic employment package.",
     "Basic employment terms do not include health insurance coverage.",
     "Health Insurance is included in the basic employment package."),
    ("The service does not store payment card numbers.",
     "Payment card numbers are never retained by the service.",
     "The service stores payment card numbers."),
    ("Access logs are not deleted for at least 12 months.",
     "Access logs are preserved for a minimum of 12 months before any deletion.",
     "Access logs are deleted within 12 months."),
    ("The medication is contraindicated in patients with renal impairment.",
     "Patients with kidney dysfunction should not receive this medication.",
     "The medication is safe for patients with renal impairment."),
    ("Physical access to server rooms is restricted to authorized personnel only.",
     "Only authorized staff may enter server room areas.",
     "Physical access to server rooms is unrestricted."),
    ("The system does not support plaintext password storage.",
     "Storing passwords in plaintext is not supported by the system.",
     "The system supports plaintext password storage."),
    ("Employees are not eligible for bonuses during the probation period.",
     "Bonus eligibility begins only after the probation period concludes.",
     "Employees are eligible for bonuses during the probation period."),
    ("The API endpoint is not publicly accessible without authentication.",
     "Authentication is required to access this API endpoint.",
     "The API endpoint is publicly accessible without authentication."),
    ("The building is not equipped with sprinkler systems.",
     "Automated fire suppression systems are absent from the building.",
     "The building is equipped with sprinkler systems."),
    ("The chemical reaction does not produce toxic byproducts.",
     "No toxic byproducts are generated during this reaction.",
     "The chemical reaction produces toxic byproducts."),
    ("Backup power is not guaranteed for more than 2 hours.",
     "Emergency generators provide a maximum of 2 hours of backup power.",
     "Backup power is guaranteed for more than 2 hours."),
    ("The policy does not cover pre-existing conditions.",
     "Pre-existing conditions are excluded from policy coverage.",
     "The policy covers pre-existing conditions."),
    ("Remote work is not permitted for roles with security clearance.",
     "Employees holding security clearances must work on-site.",
     "Remote work is permitted for roles with security clearance."),
    ("Data subjects have not consented to profiling.",
     "Profiling of these data subjects has not received consent.",
     "Data subjects have consented to profiling."),
    ("The transaction was not approved by the compliance team.",
     "Compliance team approval was not granted for this transaction.",
     "The transaction was approved by the compliance team."),
    ("Night-shift bonuses are not available for part-time employees.",
     "Part-time staff are excluded from night-shift bonus eligibility.",
     "Night-shift bonuses are available for part-time employees."),
    ("The container must not be stored above 30 degrees Celsius.",
     "Storage temperature must remain below 30 degrees Celsius.",
     "The container can be stored above 30 degrees Celsius."),
    ("The vendor does not have ISO 27001 certification.",
     "ISO 27001 certification has not been obtained by the vendor.",
     "The vendor has ISO 27001 certification."),
    ("Wireless communication is not authorized within the restricted zone.",
     "All wireless devices must be disabled in the restricted zone.",
     "Wireless communication is authorized within the restricted zone."),
    ("The patient was not placed on a ventilator.",
     "No mechanical ventilation was required for the patient.",
     "The patient was placed on a ventilator."),
    ("The software update does not break backward compatibility.",
     "Backward compatibility is fully preserved in this update.",
     "The software update breaks backward compatibility."),
    ("The compound has not been tested on human subjects.",
     "Human trials for this compound have not been conducted.",
     "The compound has been tested on human subjects."),
    ("The clause does not supersede existing agreements.",
     "Existing contracts are not overridden by this clause.",
     "The clause supersedes all existing agreements."),
    ("Log retention policies are not configurable by end users.",
     "End users cannot modify log retention settings.",
     "Log retention policies are configurable by end users."),
    ("The asset is not depreciated using straight-line method.",
     "Straight-line depreciation is not applied to this asset.",
     "The asset is depreciated using the straight-line method."),
    ("Overtime pay is not applicable for salaried exempt employees.",
     "Salaried exempt staff are ineligible for overtime compensation.",
     "Overtime pay is applicable for salaried exempt employees."),
    ("The surgical procedure was not performed under general anesthesia.",
     "General anesthesia was not administered during the procedure.",
     "The surgical procedure was performed under general anesthesia."),
    ("The system flag does not trigger an automatic account suspension.",
     "A flagged account is not automatically suspended by the system.",
     "The system flag triggers an automatic account suspension."),
    ("The legal agreement does not include an arbitration clause.",
     "No arbitration requirement exists within this legal agreement.",
     "The legal agreement includes an arbitration clause."),
    ("This endpoint is not rate limited.",
     "Rate limiting does not apply to requests on this endpoint.",
     "This endpoint is rate limited."),
    ("The report does not reflect data from deleted accounts.",
     "Deleted account data is excluded from all generated reports.",
     "The report reflects data from deleted accounts."),
]

_SUPERLATIVE: List[Tuple[str, str, str]] = [
    ("The Pro plan offers unlimited API calls per month.",
     "The Pro plan provides unlimited monthly API calls.",
     "The Pro plan offers limited API calls per month."),
    ("The free tier provides limited storage of 5GB.",
     "Free accounts are restricted to 5GB of storage.",
     "The free tier provides unlimited storage."),
    ("This is the fastest available model in the product lineup.",
     "Among all current models, this is the fastest available.",
     "This is the slowest available model in the product lineup."),
    ("The contract grants exclusive rights to the licensee.",
     "The licensee receives exclusive rights under this contract.",
     "The contract grants non-exclusive rights to the licensee."),
    ("The system provides real-time monitoring with no data delay.",
     "Monitoring data is delivered in real time with zero delay.",
     "The system provides monitoring with significant data delay."),
    ("The highest priority support tier includes guaranteed 15-minute response.",
     "Top-tier support guarantees a 15-minute response window.",
     "The lowest priority support tier includes a 15-minute response."),
    ("Enterprise accounts have unrestricted access to all API endpoints.",
     "Enterprise customers enjoy unrestricted access to every API endpoint.",
     "Enterprise accounts have restricted access to all API endpoints."),
    ("The database is capable of handling the maximum concurrent load of 10,000 users.",
     "The system can support up to 10,000 simultaneous users at peak load.",
     "The database is capable of handling a minimum concurrent load of 10,000 users."),
    ("Only the most senior administrator can approve emergency changes.",
     "Emergency change approval is reserved for the most senior administrator.",
     "Only the most junior administrator can approve emergency changes."),
    ("The platform offers the broadest cloud provider compatibility of any tool.",
     "This platform supports more cloud providers than any comparable tool.",
     "The platform offers the narrowest cloud provider compatibility."),
    ("Basic accounts are limited to a maximum of 3 team members.",
     "Teams on a basic account may not exceed 3 members.",
     "Basic accounts support an unlimited number of team members."),
    ("The medication provides the longest-lasting relief in its class.",
     "Among all drugs in its class, this provides the longest relief duration.",
     "The medication provides the shortest-lasting relief in its class."),
    ("Platinum members receive the highest cashback rate of any tier.",
     "Cashback rates are highest for members at the Platinum level.",
     "Platinum members receive the lowest cashback rate of any tier."),
    ("This is the least invasive surgical technique available.",
     "Among available surgical approaches, this is the least invasive.",
     "This is the most invasive surgical technique available."),
    ("The redundant architecture guarantees zero single points of failure.",
     "The architecture is fully redundant, eliminating all single points of failure.",
     "The architecture has multiple single points of failure."),
    ("The algorithm achieves best-in-class accuracy on the benchmark dataset.",
     "Benchmark results confirm best-in-class accuracy for this algorithm.",
     "The algorithm achieves the worst accuracy on the benchmark dataset."),
    ("Subscribers on the Annual plan enjoy the lowest per-unit price.",
     "Annual plan subscribers benefit from the most competitive per-unit pricing.",
     "Subscribers on the Annual plan pay the highest per-unit price."),
    ("The material has the highest tensile strength available in the product range.",
     "No material in the product range exceeds this tensile strength.",
     "The material has the lowest tensile strength in the product range."),
    ("Students on the premium tier have unlimited exam attempts.",
     "Premium students may retake exams an unlimited number of times.",
     "Students on the premium tier have a limited number of exam attempts."),
    ("This product carries the strictest environmental compliance certification.",
     "Environmental standards compliance for this product is at the strictest tier.",
     "This product carries the most basic environmental compliance certification."),
    ("The dedicated server plan offers the maximum available bandwidth allocation.",
     "Bandwidth allocation is at its maximum level on the dedicated server plan.",
     "The dedicated server plan offers the minimum available bandwidth."),
    ("All user activity is logged with the highest granularity possible.",
     "User activity logging captures the finest level of detail available.",
     "All user activity is logged at the lowest granularity."),
    ("The first-responder protocol is activated at the earliest sign of anomaly.",
     "Anomaly detection triggers the first-responder protocol at the earliest indication.",
     "The first-responder protocol is activated only at the latest sign of anomaly."),
    ("The most critical system components are replicated across all three regions.",
     "The highest-priority components are replicated in all three geographic regions.",
     "The least critical system components are replicated across all three regions."),
    ("Users on trial accounts face the strictest rate limits of any tier.",
     "Trial accounts are subject to the most restrictive rate-limit policies.",
     "Users on trial accounts face the most relaxed rate limits of any tier."),
    ("The device delivers the most precise temperature control on the market.",
     "No competing device provides more precise temperature control.",
     "The device delivers the least precise temperature control on the market."),
    ("Legacy tier accounts have the fewest configuration options available.",
     "Configuration options are most limited for legacy tier accounts.",
     "Legacy tier accounts have the most configuration options available."),
    ("This encryption protocol is the most widely adopted in the industry.",
     "Industry adoption of this encryption protocol is broader than any alternative.",
     "This encryption protocol is the least widely adopted in the industry."),
    ("The top-tier plan includes the highest number of custom integrations.",
     "Custom integration allowances are greatest at the top pricing tier.",
     "The entry-level plan includes the highest number of custom integrations."),
    ("The incident with the greatest business impact is assigned the highest severity.",
     "Severity classification prioritizes incidents by scale of business impact.",
     "The incident with the least business impact receives the highest severity."),
    ("Administrative users retain the broadest set of access privileges.",
     "Access privileges are at their widest scope for administrative roles.",
     "Administrative users retain the narrowest set of access privileges."),
    ("The fully managed service requires the least operational overhead.",
     "Operational effort is minimized with the fully managed service offering.",
     "The fully managed service requires the most operational overhead."),
    ("The highest availability tier guarantees a maximum of 26 minutes of downtime per year.",
     "Top availability tiers limit annual downtime to no more than 26 minutes.",
     "The lowest availability tier guarantees a maximum of 26 minutes of downtime per year."),
    ("The newest AI model delivers the greatest inference speed improvement.",
     "Speed improvements from the latest AI model surpass all predecessors.",
     "The oldest AI model delivers the greatest inference speed improvement."),
    ("The premium subscription provides the most comprehensive analytics dashboard.",
     "Analytics depth and coverage are at their greatest on the premium subscription.",
     "The premium subscription provides the least comprehensive analytics dashboard."),
    ("The minimum viable configuration requires the fewest infrastructure components.",
     "Fewer infrastructure components are needed for a minimal viable configuration.",
     "The minimum viable configuration requires the most infrastructure components."),
    ("The longest-standing client accounts receive the most favorable contract terms.",
     "Favorable contract terms are prioritized for the longest-tenured clients.",
     "Newly onboarded accounts receive the most favorable contract terms."),
    ("The fastest recovery time is achieved when warm standby is configured.",
     "Warm standby configuration yields the quickest recovery time.",
     "The slowest recovery time is achieved when warm standby is configured."),
    ("The most regulated industries receive the highest compliance support.",
     "Compliance support is deepest for the most heavily regulated sectors.",
     "The least regulated industries receive the highest compliance support."),
    ("Data processing throughput is at its peak during off-peak scheduling.",
     "Scheduling jobs during off-peak hours maximizes processing throughput.",
     "Data processing throughput is at its lowest during off-peak scheduling."),
    ("The weakest cryptographic hash function in the suite is MD5.",
     "MD5 is the least secure hashing algorithm in the supported suite.",
     "The strongest cryptographic hash function in the suite is MD5."),
    ("The least privileged access model is recommended as the security baseline.",
     "Security best practice favors the least privilege access model as the baseline.",
     "The most privileged access model is recommended as the security baseline."),
    ("The highest-traffic events trigger automatic horizontal scaling.",
     "Horizontal scaling is triggered during the highest-traffic periods.",
     "The lowest-traffic events trigger automatic horizontal scaling."),
    ("The most granular access policy is enforced at the individual resource level.",
     "Resource-level enforcement provides the most granular access control.",
     "The least granular access policy is enforced at the individual resource level."),
    ("The deepest audit trail is maintained for the highest-risk transaction types.",
     "Highest-risk transactions are tracked with the most detailed audit trail.",
     "The shallowest audit trail is maintained for the highest-risk transaction types."),
    ("The broadest set of compliance frameworks is supported at the enterprise tier.",
     "Enterprise-tier accounts have access to the widest range of compliance frameworks.",
     "The fewest compliance frameworks are supported at the enterprise tier."),
    ("The most severe security incidents are escalated immediately to senior engineers.",
     "Immediate escalation to senior engineers applies to the highest severity incidents.",
     "The least severe security incidents are escalated immediately to senior engineers."),
    ("The highest-capacity storage tier supports the largest single file uploads.",
     "Maximum single-file upload size is supported on the highest-capacity storage tier.",
     "The lowest-capacity storage tier supports the largest single file uploads."),
    ("The most experienced support agents handle enterprise account inquiries.",
     "Enterprise account support is staffed by the most experienced agents.",
     "The least experienced support agents handle enterprise account inquiries."),
    ("The lowest latency region is recommended for latency-sensitive workloads.",
     "Latency-sensitive applications should be deployed in the lowest-latency region.",
     "The highest latency region is recommended for latency-sensitive workloads."),
]
# fmt: on

assert len(_NUMERICAL) == 50, f"Expected 50 numerical pairs, got {len(_NUMERICAL)}"
assert len(_NEGATION) == 50, f"Expected 50 negation pairs, got {len(_NEGATION)}"
assert len(_SUPERLATIVE) == 50, f"Expected 50 superlative pairs, got {len(_SUPERLATIVE)}"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2  Case model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AdversarialCase:
    """Immutable descriptor for one benchmark test case."""
    case_id: int
    category: str          # "numerical" | "negation" | "superlative"
    adversarial: bool      # True → hallucinated; False → faithful ground truth
    source_document: str
    ai_response: str
    expected_verdict: str  # "UNSUPPORTED" (adversarial) | "VERIFIED" (faithful)


def _build_dataset() -> List[AdversarialCase]:
    """Construct the full 300-case dataset from the raw pair tables."""
    cases: List[AdversarialCase] = []
    cid = 1

    categories = [
        ("numerical",   _NUMERICAL),
        ("negation",    _NEGATION),
        ("superlative", _SUPERLATIVE),
    ]

    for cat_name, pairs in categories:
        for src, faithful, adversarial_claim in pairs:
            cases.append(AdversarialCase(
                case_id=cid,
                category=cat_name,
                adversarial=False,
                source_document=src,
                ai_response=faithful,
                expected_verdict="VERIFIED",
            ))
            cid += 1
            cases.append(AdversarialCase(
                case_id=cid,
                category=cat_name,
                adversarial=True,
                source_document=src,
                ai_response=adversarial_claim,
                expected_verdict="UNSUPPORTED",
            ))
            cid += 1

    assert len(cases) == 300, f"Dataset size mismatch: expected 300, got {len(cases)}"
    return cases


DATASET: List[AdversarialCase] = _build_dataset()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3  Result types
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CaseResult:
    """Outcome of running a single AdversarialCase against the live API."""
    case_id: int
    category: str
    adversarial: bool

    # Ground truth
    expected_verdict: str
    ai_response: str
    source_document: str

    # API response
    primary_status: str        # status of the first (and usually only) claim
    all_unsupported: bool      # True when every claim is UNSUPPORTED
    similarity_score: float    # similarity_score of primary claim

    # Classification
    correct: bool              # did TL agree with expected_verdict?
    is_false_positive: bool    # adversarial case TL missed (claimed faithful)
    is_false_negative: bool    # faithful case TL over-flagged as UNSUPPORTED

    latency_ms: float
    error: Optional[str] = None


@dataclass
class CategoryStats:
    category: str
    total: int = 0
    tp: int = 0   # adversarial correctly flagged UNSUPPORTED
    tn: int = 0   # faithful correctly left as non-UNSUPPORTED
    fp: int = 0   # adversarial slipped through as non-UNSUPPORTED  ← critical miss
    fn: int = 0   # faithful over-flagged as UNSUPPORTED

    precision: float = 0.0    # TP / (TP + FP)
    recall: float    = 0.0    # TP / (TP + FN)
    f1: float        = 0.0
    accuracy: float  = 0.0
    avg_latency_ms: float = 0.0
    avg_similarity: float = 0.0


@dataclass
class BenchmarkReport:
    """Serialisable top-level report written to JSON."""
    schema_version: str = "1.0"
    timestamp: str = ""
    api_url: str = ""
    git_branch: str = ""

    total_cases: int = 0
    cases_executed: int = 0
    aborted: bool = False

    # per-category
    numerical: Optional[Dict]   = None
    negation: Optional[Dict]    = None
    superlative: Optional[Dict] = None

    # overall
    overall_precision: float = 0.0
    overall_recall: float    = 0.0
    overall_f1: float        = 0.0
    overall_accuracy: float  = 0.0
    total_false_positives: int = 0
    total_false_negatives: int = 0
    avg_latency_ms: float    = 0.0
    total_duration_sec: float = 0.0

    case_results: List[Dict] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4  Core execution
# ══════════════════════════════════════════════════════════════════════════════

def _run_case(client: TruthLayer, case: AdversarialCase) -> CaseResult:
    """
    Execute one test case.  Uses the typed Claim dataclass from the SDK —
    never treats Claim objects as dicts.
    """
    t0 = time.perf_counter()
    error: Optional[str] = None
    primary_status = "ERROR"
    all_unsupported = False
    similarity: float = 0.0

    try:
        result: VerificationResult = client.verify(
            ai_response=case.ai_response,
            source_documents=[case.source_document],
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        claims: List[Claim] = result.claims
        if claims:
            primary: Claim = claims[0]
            primary_status = primary.status          # typed attribute, not .get()
            similarity = primary.similarity_score    # typed attribute, not .get()

        # "all UNSUPPORTED" = TruthLayer is confident this is hallucinated
        all_unsupported = bool(claims) and all(c.status == "UNSUPPORTED" for c in claims)

    except TruthLayerError as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        error = str(exc)

    # ── Correctness  ──────────────────────────────────────────────────────────
    #   expected UNSUPPORTED → correct iff every claim is UNSUPPORTED
    #   expected VERIFIED    → correct iff NOT every claim is UNSUPPORTED
    if case.expected_verdict == "UNSUPPORTED":
        correct = all_unsupported
    else:
        correct = not all_unsupported

    is_fp = case.adversarial and not all_unsupported   # missed hallucination
    is_fn = (not case.adversarial) and all_unsupported # over-flagged faithful

    return CaseResult(
        case_id=case.case_id,
        category=case.category,
        adversarial=case.adversarial,
        expected_verdict=case.expected_verdict,
        ai_response=case.ai_response,
        source_document=case.source_document,
        primary_status=primary_status,
        all_unsupported=all_unsupported,
        similarity_score=round(similarity, 4),
        correct=correct,
        is_false_positive=is_fp,
        is_false_negative=is_fn,
        latency_ms=round(elapsed_ms, 2),
        error=error,
    )


def _compute_stats(category: str, results: List[CaseResult]) -> CategoryStats:
    stats = CategoryStats(category=category, total=len(results))
    if not results:
        return stats

    latencies: List[float] = []
    sims: List[float] = []

    for r in results:
        latencies.append(r.latency_ms)
        sims.append(r.similarity_score)

        if r.adversarial:
            if r.all_unsupported:
                stats.tp += 1
            else:
                stats.fp += 1
        else:
            if not r.all_unsupported:
                stats.tn += 1
            else:
                stats.fn += 1

    denom_p  = stats.tp + stats.fp
    denom_r  = stats.tp + stats.fn
    denom_a  = len(results)

    stats.precision     = stats.tp / denom_p              if denom_p  else 1.0
    stats.recall        = stats.tp / denom_r              if denom_r  else 1.0
    f1_denom            = stats.precision + stats.recall
    stats.f1            = (2 * stats.precision * stats.recall / f1_denom) if f1_denom else 0.0
    stats.accuracy      = (stats.tp + stats.tn) / denom_a if denom_a  else 0.0
    stats.avg_latency_ms= round(sum(latencies) / len(latencies), 2)
    stats.avg_similarity= round(sum(sims) / len(sims), 4)

    # Round percentages for readability
    stats.precision = round(stats.precision * 100, 2)
    stats.recall    = round(stats.recall    * 100, 2)
    stats.f1        = round(stats.f1        * 100, 2)
    stats.accuracy  = round(stats.accuracy  * 100, 2)

    return stats


def _git_branch() -> str:
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5  Reporting
# ══════════════════════════════════════════════════════════════════════════════

_W = 72  # console width

def _banner(text: str) -> None:
    print("=" * _W)
    print(f"  {text}")
    print("=" * _W)


def _section(text: str) -> None:
    print(f"\n  ── {text} {'─' * (_W - 6 - len(text))}")


def _print_category(stats: CategoryStats) -> None:
    label = {
        "numerical":   "A  Numerical Mismatch   (100 cases)",
        "negation":    "B  Negation Flip         (100 cases)",
        "superlative": "C  Superlative Swap      (100 cases)",
    }.get(stats.category, stats.category)

    _section(f"Category {label}")
    fp_marker = "  ← CRITICAL" if stats.fp > 0 else ""
    print(f"     Precision  (hallucinations caught):  {stats.precision:>6.2f}%")
    print(f"     Recall     (faithful preserved):     {stats.recall:>6.2f}%")
    print(f"     F1 Score:                            {stats.f1:>6.2f}%")
    print(f"     Accuracy:                            {stats.accuracy:>6.2f}%")
    print(f"     True  Positives (TP):  {stats.tp:>4}   adversarial correctly flagged")
    print(f"     True  Negatives (TN):  {stats.tn:>4}   faithful correctly passed")
    print(f"     False Positives (FP):  {stats.fp:>4}   hallucination missed{fp_marker}")
    print(f"     False Negatives (FN):  {stats.fn:>4}   faithful over-flagged")
    print(f"     Avg latency:           {stats.avg_latency_ms:>6.0f} ms")
    print(f"     Avg similarity score:  {stats.avg_similarity:>8.4f}")


def _print_report(
    results: List[CaseResult],
    cat_stats: Dict[str, CategoryStats],
    overall: CategoryStats,
    duration: float,
    api_url: str,
    aborted: bool,
) -> None:
    print()
    _banner("TruthLayer Adversarial Benchmark — Final Results")
    print(f"  {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  API: {api_url}")
    if aborted:
        print("  *** RUN WAS ABORTED EARLY via --fail-fast ***")

    for cat in ("numerical", "negation", "superlative"):
        if cat in cat_stats:
            _print_category(cat_stats[cat])

    _section(f"Overall  ({len(results)} / 300 cases executed)")
    fp_marker = "  ← HALLUCINATIONS ESCAPED" if overall.fp > 0 else "  ← ZERO ESCAPES"
    print(f"     Precision:   {overall.precision:>6.2f}%")
    print(f"     Recall:      {overall.recall:>6.2f}%")
    print(f"     F1:          {overall.f1:>6.2f}%")
    print(f"     Accuracy:    {overall.accuracy:>6.2f}%")
    print(f"     False Positives (missed hallucinations): {overall.fp:>3}{fp_marker}")
    print(f"     False Negatives (over-flagged):          {overall.fn:>3}")
    print(f"     Avg latency: {overall.avg_latency_ms:>6.0f} ms")
    print(f"     Duration:    {duration:.1f}s")
    print("=" * _W)
    print()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="TruthLayer 300-Case Adversarial Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output", "-o", default="",
        help="Directory to write JSON results (omit to skip)",
    )
    parser.add_argument(
        "--category", "-c",
        choices=["numerical", "negation", "superlative", "all"],
        default="all",
        help="Category subset to run (default: all)",
    )
    parser.add_argument(
        "--fail-fast", "-f", action="store_true",
        help="Abort on first False Positive (missed hallucination)",
    )
    parser.add_argument(
        "--delay", "-d", type=float, default=0.1,
        help="Seconds between API calls to avoid rate limiting (default: 0.1)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print every case result inline (default: summary only)",
    )
    args = parser.parse_args()

    # ── env vars ──────────────────────────────────────────────────────────────
    api_url = os.environ.get("TRUTHLAYER_API_URL", "").rstrip("/")
    api_key = os.environ.get("TRUTHLAYER_API_KEY", "")
    if not api_url or not api_key:
        print("Error: Set required environment variables before running:")
        print('  $env:TRUTHLAYER_API_URL = "https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod"')
        print('  $env:TRUTHLAYER_API_KEY = "tl_your_key_here"')
        return 1

    # ── dataset selection ─────────────────────────────────────────────────────
    cases = DATASET if args.category == "all" else [
        c for c in DATASET if c.category == args.category
    ]

    client = TruthLayer(api_key=api_key, api_url=api_url, timeout=60)

    # ── header ────────────────────────────────────────────────────────────────
    branch = _git_branch()
    _banner("TruthLayer Adversarial Benchmark Suite")
    print(f"  Cases:   {len(cases)} ({args.category})")
    print(f"  API:     {api_url}")
    print(f"  Branch:  {branch}")
    print(f"  Started: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * _W)

    # ── health check ──────────────────────────────────────────────────────────
    try:
        health = client.health()
        status = health.get("status", "unknown")
        print(f"\n  API Health: {status}  OK\n")
    except Exception as exc:
        print(f"\n  ERROR: API unreachable — {exc}")
        return 1

    # ── run ───────────────────────────────────────────────────────────────────
    cat_labels = {"numerical": "A", "negation": "B", "superlative": "C"}
    results: List[CaseResult] = []
    aborted = False
    suite_start = time.perf_counter()

    for idx, case in enumerate(cases, 1):
        res = _run_case(client, case)
        results.append(res)

        if args.verbose:
            flag   = "ADV" if case.adversarial else "FAITH"
            status = "OK  " if res.correct else "FAIL"
            fp_tag = " ** FP" if res.is_false_positive else ""
            fn_tag = " ** FN" if res.is_false_negative else ""
            sim    = f"{res.similarity_score:.3f}"
            print(
                f"  [{idx:3d}/{len(cases)}] Cat {cat_labels.get(case.category,'?')} "
                f"| {flag:5s} | {status} | {res.latency_ms:6.0f}ms | sim={sim}"
                f"{fp_tag}{fn_tag} | {case.ai_response[:52]}"
            )
        else:
            # Condensed progress: print only failures inline
            if not res.correct:
                tag = "FP" if res.is_false_positive else "FN"
                print(
                    f"  [{idx:3d}] {tag} | cat={case.category:11s} | "
                    f"sim={res.similarity_score:.3f} | {case.ai_response[:55]}"
                )

        if args.fail_fast and res.is_false_positive:
            print(f"\n  *** FAIL-FAST: false positive on case {case.case_id} ***")
            aborted = True
            break

        if args.delay > 0:
            time.sleep(args.delay)

    total_duration = time.perf_counter() - suite_start

    # ── stats ─────────────────────────────────────────────────────────────────
    cat_stats: Dict[str, CategoryStats] = {}
    for cat in ("numerical", "negation", "superlative"):
        subset = [r for r in results if r.category == cat]
        if subset:
            cat_stats[cat] = _compute_stats(cat, subset)

    overall = _compute_stats("overall", results)

    # ── console report ────────────────────────────────────────────────────────
    _print_report(results, cat_stats, overall, total_duration, api_url, aborted)

    # ── JSON output ───────────────────────────────────────────────────────────
    if args.output:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"adversarial_{ts}.json"

        report = BenchmarkReport(
            timestamp=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            api_url=api_url,
            git_branch=branch,
            total_cases=len(cases),
            cases_executed=len(results),
            aborted=aborted,
            numerical=asdict(cat_stats["numerical"])   if "numerical"   in cat_stats else None,
            negation=asdict(cat_stats["negation"])     if "negation"    in cat_stats else None,
            superlative=asdict(cat_stats["superlative"]) if "superlative" in cat_stats else None,
            overall_precision=overall.precision,
            overall_recall=overall.recall,
            overall_f1=overall.f1,
            overall_accuracy=overall.accuracy,
            total_false_positives=overall.fp,
            total_false_negatives=overall.fn,
            avg_latency_ms=overall.avg_latency_ms,
            total_duration_sec=round(total_duration, 2),
            case_results=[asdict(r) for r in results],
        )

        with open(out_file, "w", encoding="utf-8") as fh:
            json.dump(asdict(report), fh, indent=2, ensure_ascii=False)

        print(f"  Results written to: {out_file}\n")

    # exit 1 if any hallucination escaped (useful in CI)
    return 1 if overall.fp > 0 or aborted else 0


if __name__ == "__main__":
    sys.exit(main())
