"""Seed data for IPL Auction — real players and 5 teams."""

TEAMS = [
    {
        "name": "Mumbai Indians",
        "short_name": "MI",
        "color": "#004BA0",
        "color_secondary": "#D4A843",
        "logo_emoji": "🔵",
    },
    {
        "name": "Chennai Super Kings",
        "short_name": "CSK",
        "color": "#F9CD05",
        "color_secondary": "#1B2133",
        "logo_emoji": "🦁",
    },
    {
        "name": "Royal Challengers Bengaluru",
        "short_name": "RCB",
        "color": "#E4002B",
        "color_secondary": "#2B2B2B",
        "logo_emoji": "🔴",
    },
    {
        "name": "Kolkata Knight Riders",
        "short_name": "KKR",
        "color": "#3A225D",
        "color_secondary": "#D4A843",
        "logo_emoji": "💜",
    },
    {
        "name": "Delhi Capitals",
        "short_name": "DC",
        "color": "#17479E",
        "color_secondary": "#EF1B23",
        "logo_emoji": "🦅",
    },
]

# Players: (name, role, nationality, base_price_in_lakhs, set_number)
# Set 1: Marquee (200L = 2Cr)
# Set 2: Capped Stars (100L = 1Cr)
# Set 3: Mid-tier (50L = 50L)
# Set 4: Uncapped/Young (20L = 20L)

PLAYERS = [
    # ── SET 1: MARQUEE (Base: ₹2 Cr) ──
    ("Virat Kohli", "BAT", "IND", 200, 1),
    ("Rohit Sharma", "BAT", "IND", 200, 1),
    ("Jasprit Bumrah", "BOWL", "IND", 200, 1),
    ("Suryakumar Yadav", "BAT", "IND", 200, 1),
    ("Pat Cummins", "BOWL", "OVERSEAS", 200, 1),
    ("Rashid Khan", "BOWL", "OVERSEAS", 200, 1),
    ("Jos Buttler", "WK", "OVERSEAS", 200, 1),
    ("Rishabh Pant", "WK", "IND", 200, 1),

    # ── SET 2: CAPPED STARS (Base: ₹1 Cr) ──
    ("KL Rahul", "WK", "IND", 100, 2),
    ("Shubman Gill", "BAT", "IND", 100, 2),
    ("Hardik Pandya", "AR", "IND", 100, 2),
    ("Ravindra Jadeja", "AR", "IND", 100, 2),
    ("Mohammed Shami", "BOWL", "IND", 100, 2),
    ("Yuzvendra Chahal", "BOWL", "IND", 100, 2),
    ("Shreyas Iyer", "BAT", "IND", 100, 2),
    ("Ishan Kishan", "WK", "IND", 100, 2),
    ("Mitchell Starc", "BOWL", "OVERSEAS", 100, 2),
    ("Trent Boult", "BOWL", "OVERSEAS", 100, 2),
    ("David Warner", "BAT", "OVERSEAS", 100, 2),
    ("Glenn Maxwell", "AR", "OVERSEAS", 100, 2),
    ("Kagiso Rabada", "BOWL", "OVERSEAS", 100, 2),
    ("Faf du Plessis", "BAT", "OVERSEAS", 100, 2),

    # ── SET 3: MID-TIER (Base: ₹50 L) ──
    ("Axar Patel", "AR", "IND", 50, 3),
    ("Kuldeep Yadav", "BOWL", "IND", 50, 3),
    ("Devdutt Padikkal", "BAT", "IND", 50, 3),
    ("Sanju Samson", "WK", "IND", 50, 3),
    ("Shardul Thakur", "AR", "IND", 50, 3),
    ("Deepak Chahar", "BOWL", "IND", 50, 3),
    ("Washington Sundar", "AR", "IND", 50, 3),
    ("Ruturaj Gaikwad", "BAT", "IND", 50, 3),
    ("Marcus Stoinis", "AR", "OVERSEAS", 50, 3),
    ("Quinton de Kock", "WK", "OVERSEAS", 50, 3),
    ("Sunil Narine", "AR", "OVERSEAS", 50, 3),
    ("Andre Russell", "AR", "OVERSEAS", 50, 3),
    ("Sam Curran", "AR", "OVERSEAS", 50, 3),
    ("Wanindu Hasaranga", "BOWL", "OVERSEAS", 50, 3),
    ("Anrich Nortje", "BOWL", "OVERSEAS", 50, 3),
    ("Heinrich Klaasen", "WK", "OVERSEAS", 50, 3),

    # ── SET 4: UNCAPPED / YOUNG (Base: ₹20 L) ──
    ("Yashasvi Jaiswal", "BAT", "IND", 20, 4),
    ("Rinku Singh", "BAT", "IND", 20, 4),
    ("Dhruv Jurel", "WK", "IND", 20, 4),
    ("Tilak Varma", "BAT", "IND", 20, 4),
    ("Jitesh Sharma", "WK", "IND", 20, 4),
    ("Avesh Khan", "BOWL", "IND", 20, 4),
    ("Arshdeep Singh", "BOWL", "IND", 20, 4),
    ("Mukesh Kumar", "BOWL", "IND", 20, 4),
    ("Ravi Bishnoi", "BOWL", "IND", 20, 4),
    ("Abhishek Sharma", "AR", "IND", 20, 4),
    ("Tushar Deshpande", "BOWL", "IND", 20, 4),
    ("Matheesha Pathirana", "BOWL", "OVERSEAS", 20, 4),
    ("Tim David", "BAT", "OVERSEAS", 20, 4),
    ("Phil Salt", "WK", "OVERSEAS", 20, 4),
]


import json
import random

def seed_auction(db, Auction, Team, Player, room_code):
    """Create a new auction with teams and players."""
    auction = Auction(room_code=room_code, status="waiting")
    db.session.add(auction)
    db.session.flush()

    for team_data in TEAMS:
        team = Team(
            name=team_data["name"],
            short_name=team_data["short_name"],
            color=team_data["color"],
            color_secondary=team_data["color_secondary"],
            logo_emoji=team_data["logo_emoji"],
            purse_remaining=10000.0,  # 100 Cr = 10000 Lakhs
            auction_id=auction.id,
        )
        db.session.add(team)

    for pname, role, nationality, base_price, set_num in PLAYERS:
        from typing import Any, Dict
        # Generate realistic random stats based on role
        stats: Dict[str, Any] = {"Matches": random.randint(30, 150)}
        if role in ["BAT", "WK"]:
            stats["Runs"] = random.randint(800, 4500)
            stats["Avg"] = float(f"{random.uniform(25.0, 45.0):.2f}")
            stats["SR"] = float(f"{random.uniform(120.0, 160.0):.2f}")
        elif role == "BOWL":
            stats["Wickets"] = random.randint(40, 150)
            stats["Econ"] = float(f"{random.uniform(6.5, 9.5):.2f}")
            stats["Avg"] = float(f"{random.uniform(18.0, 30.0):.2f}")
        elif role == "AR":
            stats["Runs"] = random.randint(500, 2500)
            stats["SR"] = float(f"{random.uniform(130.0, 170.0):.2f}")
            stats["Wickets"] = random.randint(30, 100)
            stats["Econ"] = float(f"{random.uniform(7.0, 9.5):.2f}")

        player = Player(
            name=pname,
            role=role,
            nationality=nationality,
            base_price=base_price,
            set_number=set_num,
            stats_json=json.dumps(stats),
            auction_id=auction.id,
        )
        db.session.add(player)

    db.session.commit()
    return auction

