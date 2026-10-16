"""Seed demo data (clearly fictional) for local development."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.models.entities import Company, IdealCustomerProfile, Lead  # noqa: E402
from app.services.scoring import default_icp  # noqa: E402

DEMOS = [
    ("Lilongwe Fresh Produce Ltd (demo)", "Malawi", "agriculture", "51-200",
     "Chikondi Banda", "Managing Director", "chikondi@lilongwe-fresh.demo"),
    ("Blantyre Freight & Logistics (demo)", "Malawi", "logistics", "51-200",
     "Mphatso Kaimfa", "Head of Operations", "mphatso@blantyre-freight.demo"),
    ("Zomba Textiles Cooperative (demo)", "Malawi", "manufacturing", "11-50",
     "Tawonga Phiri", "Founder", "tawonga@zomba-textiles.demo"),
    ("Lusaka PayBridge (demo)", "Zambia", "fintech", "11-50",
     "Mutinta Hamoonga", "CEO", "mutinta@paybridge.demo"),
    ("Kigali Cold Chain (demo)", "Rwanda", "logistics", "201-500",
     "Aline Uwase", "Operations Manager", "aline@kigali-coldchain.demo"),
    ("Accra MarketLink (demo)", "Ghana", "retail", "51-200",
     "Kwame Mensah", "Sales Lead", "kwame@marketlink.demo"),
    ("Nairobi AgriSensors (demo)", "Kenya", "agriculture", "11-50",
     "Wanjiru Njoroge", "CTO", "wanjiru@agrisensors.demo"),
    ("Cape Town SolarServe (demo)", "South Africa", "manufacturing", "201-500",
     "Pieter van Wyk", "Procurement Head", "pieter@solarserve.demo"),
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if not db.query(IdealCustomerProfile).first():
            db.add(IdealCustomerProfile(**default_icp()))
        for cname, country, industry, size, person, title, email in DEMOS:
            co = db.query(Company).filter(Company.name == cname).first()
            if co is None:
                co = Company(name=cname, country=country, industry=industry,
                             employee_range=size, source="demo_seed",
                             description=f"Fictional demo company for portfolio use ({industry} in {country}).")
                db.add(co)
                db.flush()
            if not db.query(Lead).filter(Lead.email == email).first():
                db.add(Lead(company_id=co.id, full_name=person, job_title=title,
                            email=email, source="demo_seed"))
        db.commit()
        print(f"Seeded {len(DEMOS)} demo leads (fictional).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
