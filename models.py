from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Auction(db.Model):
    __tablename__ = "auctions"
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(10), unique=True, nullable=False)
    status = db.Column(db.String(20), default="waiting")  # waiting, live, paused, completed
    current_player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)
    current_set = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teams = db.relationship("Team", backref="auction", lazy=True)
    players = db.relationship("Player", backref="auction", lazy=True, foreign_keys="Player.auction_id")


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    short_name = db.Column(db.String(5), nullable=False)
    color = db.Column(db.String(7), nullable=False)
    color_secondary = db.Column(db.String(7), nullable=False)
    logo_emoji = db.Column(db.String(5), default="🏏")
    purse_remaining = db.Column(db.Float, default=10000.0)  # in lakhs (100 Cr = 10000 L)
    auction_id = db.Column(db.Integer, db.ForeignKey("auctions.id"), nullable=False)
    is_connected = db.Column(db.Boolean, default=False)
    sid = db.Column(db.String(100), nullable=True)  # Socket.IO session id

    players = db.relationship("Player", backref="team", lazy=True)
    bids = db.relationship("Bid", backref="team", lazy=True)


class Player(db.Model):
    __tablename__ = "players"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # BAT, BOWL, AR, WK
    nationality = db.Column(db.String(10), nullable=False)  # IND, OVERSEAS
    base_price = db.Column(db.Float, nullable=False)  # in lakhs
    sold_price = db.Column(db.Float, nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    auction_id = db.Column(db.Integer, db.ForeignKey("auctions.id"), nullable=False)
    is_sold = db.Column(db.Boolean, default=False)
    is_unsold = db.Column(db.Boolean, default=False)
    set_number = db.Column(db.Integer, default=1)
    image_url = db.Column(db.String(255), nullable=True)
    stats_json = db.Column(db.Text, nullable=True)

    bids = db.relationship("Bid", backref="player", lazy=True)


class Bid(db.Model):
    __tablename__ = "bids"
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # in lakhs
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
