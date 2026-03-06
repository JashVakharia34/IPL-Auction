import os
import sys
import string
import random
from datetime import datetime
from functools import wraps
from typing import Any, Dict
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from config import Config
from models import db, Auction, Team, Player, Bid
from seed import seed_auction

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
# Use eventlet in production (gunicorn), threading for local development
if 'gunicorn' in sys.modules:
    async_mode = 'eventlet'
else:
    async_mode = 'threading'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

# In-memory auction state for timers
auction_timers: Dict[str, Dict[str, Any]] = {}

# ─── MIDDLEWARE DEFINITIONS ───

def auctioneer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'auctioneer':
            return redirect(url_for('index', error='Unauthorized: Auctioneer access required'))
        return f(*args, **kwargs)
    return decorated_function

def team_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['team', 'auctioneer']:
            return redirect(url_for('index', error='Unauthorized: Team access required'))
        return f(*args, **kwargs)
    return decorated_function



def generate_room_code():
    """Generate a 6-character alphanumeric room code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def format_price(lakhs):
    """Format price in lakhs to a readable string."""
    if lakhs >= 100:
        cr = lakhs / 100
        if cr == int(cr):
            return f"₹{int(cr)} Cr"
        return f"₹{cr:.2f} Cr"
    return f"₹{int(lakhs)} L"


def get_bid_increment(current_amount):
    """Get the next bid increment based on current amount."""
    if current_amount < 100:  # < 1 Cr
        return 5  # 5 Lakhs
    elif current_amount < 500:  # 1-5 Cr
        return 10  # 10 Lakhs
    elif current_amount < 1000:  # 5-10 Cr
        return 25  # 25 Lakhs
    else:  # > 10 Cr
        return 50  # 50 Lakhs


def get_player_data(player):
    """Serialize a player to dict."""
    return {
        "id": player.id,
        "name": player.name,
        "role": player.role,
        "nationality": player.nationality,
        "base_price": player.base_price,
        "base_price_formatted": format_price(player.base_price),
        "sold_price": player.sold_price,
        "sold_price_formatted": format_price(player.sold_price) if player.sold_price else None,
        "team_id": player.team_id,
        "is_sold": player.is_sold,
        "is_unsold": player.is_unsold,
        "set_number": player.set_number,
    }


def get_team_data(team):
    """Serialize a team to dict."""
    squad = Player.query.filter_by(team_id=team.id, is_sold=True).all()
    return {
        "id": team.id,
        "name": team.name,
        "short_name": team.short_name,
        "color": team.color,
        "color_secondary": team.color_secondary,
        "logo_emoji": team.logo_emoji,
        "purse_remaining": team.purse_remaining,
        "purse_formatted": format_price(team.purse_remaining),
        "is_connected": team.is_connected,
        "squad_count": len(squad),
        "squad": [get_player_data(p) for p in squad],
    }


# ─── ROUTES ───

@app.route("/")
def index():
    # If already logged in, redirect to respective dashboard
    if session.get('role') == 'auctioneer':
        return redirect(url_for('auctioneer_dashboard'))
    elif session.get('role') == 'team':
        return redirect(url_for('team_dashboard'))
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    role = data.get("role")
    password = data.get("password")
    
    if role == "auctioneer" and password == app.config["AUCTIONEER_PASSWORD"]:
        session["role"] = "auctioneer"
        return jsonify({"success": True, "redirect": url_for("auctioneer_dashboard")})
    elif role == "team" and password == app.config["TEAM_PASSWORD"]:
        session["role"] = "team"
        return jsonify({"success": True, "redirect": url_for("team_dashboard")})
    
    return jsonify({"success": False, "message": "Invalid password"}), 401

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/auctioneer")
@auctioneer_required
def auctioneer_dashboard():
    active_auctions = Auction.query.order_by(Auction.created_at.desc()).all()
    return render_template("auctioneer_dashboard.html", auctions=active_auctions)

@app.route("/team")
@team_required
def team_dashboard():
    return render_template("team_dashboard.html")


@app.route("/admin/<room_code>")
@auctioneer_required
def admin_panel(room_code):
    auction = Auction.query.filter_by(room_code=room_code).first()
    if not auction:
        return "Auction not found", 404
    return render_template("auction.html", room_code=room_code, is_admin=True)


@app.route("/auction/<room_code>/<int:team_id>")
@team_required
def auction_room(room_code, team_id):
    auction = Auction.query.filter_by(room_code=room_code).first()
    if not auction:
        return "Auction not found", 404
    team = Team.query.get(team_id)
    if not team or team.auction_id != auction.id:
        return "Team not found", 404
    return render_template("auction.html", room_code=room_code, is_admin=False, team_id=team_id)


@app.route("/api/create-auction", methods=["POST"])
@auctioneer_required
def create_auction():
    try:
        room_code = generate_room_code()
        auction = seed_auction(db, Auction, Team, Player, room_code)
        return jsonify({
            "room_code": auction.room_code,
            "admin_url": f"/admin/{auction.room_code}",
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/auction/<room_code>")
def get_auction(room_code):
    auction = Auction.query.filter_by(room_code=room_code).first()
    if not auction:
        return jsonify({"error": "Auction not found"}), 404
    teams = Team.query.filter_by(auction_id=auction.id).all()
    players = Player.query.filter_by(auction_id=auction.id).all()

    current_player = None
    if auction.current_player_id:
        p = Player.query.get(auction.current_player_id)
        if p:
            current_player = get_player_data(p)
            # Add current bid info
            highest_bid = Bid.query.filter_by(player_id=p.id).order_by(Bid.amount.desc()).first()
            if highest_bid:
                bidding_team = Team.query.get(highest_bid.team_id)
                current_player["current_bid"] = highest_bid.amount
                current_player["current_bid_formatted"] = format_price(highest_bid.amount)
                current_player["current_bid_team_id"] = highest_bid.team_id
                current_player["current_bid_team_name"] = bidding_team.short_name if bidding_team else None
                current_player["next_bid"] = highest_bid.amount + get_bid_increment(highest_bid.amount)
                current_player["next_bid_formatted"] = format_price(highest_bid.amount + get_bid_increment(highest_bid.amount))
            else:
                current_player["current_bid"] = None
                current_player["next_bid"] = p.base_price
                current_player["next_bid_formatted"] = format_price(p.base_price)

    timer_state = auction_timers.get(room_code, {})

    return jsonify({
        "room_code": auction.room_code,
        "status": auction.status,
        "current_set": auction.current_set,
        "current_player": current_player,
        "teams": [get_team_data(t) for t in teams],
        "players": [get_player_data(p) for p in players],
        "seconds_left": timer_state.get("seconds_left", 60),
    })


# ─── SOCKET.IO EVENTS ───

@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    # Mark team as disconnected
    team = Team.query.filter_by(sid=request.sid).first()
    if team:
        team.is_connected = False
        db.session.commit()
        emit("team_status", {"team_id": team.id, "is_connected": False}, room=f"auction_{team.auction.room_code}")


@socketio.on("join_auction")
def handle_join(data):
    room_code = data.get("room_code")
    team_id = data.get("team_id")  # None for admin
    is_admin = data.get("is_admin", False)

    auction = Auction.query.filter_by(room_code=room_code).first()
    if not auction:
        emit("error", {"message": "Auction not found"})
        return

    room = f"auction_{room_code}"
    join_room(room)

    if not is_admin and team_id:
        team = Team.query.get(team_id)
        if team and team.auction_id == auction.id:
            team.is_connected = True
            team.sid = request.sid
            db.session.commit()
            emit("team_status", {"team_id": team.id, "is_connected": True}, room=room)
            print(f"Team {team.short_name} joined auction {room_code}")

    emit("joined", {"room_code": room_code, "is_admin": is_admin})


@socketio.on("next_player")
def handle_next_player(data):
    room_code = data.get("room_code")
    auction = Auction.query.filter_by(room_code=room_code).first()
    if not auction:
        return

    # Find next unsold player in current set
    player = Player.query.filter_by(
        auction_id=auction.id,
        is_sold=False,
        is_unsold=False,
        set_number=auction.current_set,
    ).first()

    # If no more players in current set, move to next set
    if not player:
        next_set = auction.current_set + 1
        if next_set > 4:
            # Check for unsold players for a second round
            player = Player.query.filter_by(
                auction_id=auction.id,
                is_sold=False,
                is_unsold=True,
            ).first()
            if player:
                player.is_unsold = False  # Reset for re-auction
                db.session.commit()
            else:
                # Auction complete!
                auction.status = "completed"
                auction.current_player_id = None
                db.session.commit()
                emit("auction_complete", {}, room=f"auction_{room_code}")
                return
        else:
            auction.current_set = next_set
            player = Player.query.filter_by(
                auction_id=auction.id,
                is_sold=False,
                is_unsold=False,
                set_number=next_set,
            ).first()
            if not player:
                # Skip empty sets
                for s in range(next_set + 1, 5):
                    player = Player.query.filter_by(
                        auction_id=auction.id,
                        is_sold=False,
                        is_unsold=False,
                        set_number=s,
                    ).first()
                    if player:
                        auction.current_set = s
                        break

    if not player:
        auction.status = "completed"
        auction.current_player_id = None
        db.session.commit()
        emit("auction_complete", {}, room=f"auction_{room_code}")
        return

    # Clear previous bids for this player (in case of re-auction)
    Bid.query.filter_by(player_id=player.id).delete()
    db.session.commit()

    auction.current_player_id = player.id
    auction.status = "live"
    db.session.commit()

    player_data = get_player_data(player)
    player_data["current_bid"] = None
    player_data["next_bid"] = player.base_price
    player_data["next_bid_formatted"] = format_price(player.base_price)

    room = f"auction_{room_code}"
    emit("new_player", {"player": player_data, "set_number": auction.current_set}, room=room)

    # Start 60-second timer
    start_timer(room_code, player.id)


def start_timer(room_code, player_id):
    """Start a 60-second countdown timer for bidding."""
    # Stop existing timer if any
    if room_code in auction_timers:
        auction_timers[room_code]["running"] = False

    auction_timers[room_code] = {
        "seconds_left": 60,
        "running": True,
        "player_id": player_id,
    }

    def countdown():
        while True:
            socketio.sleep(1)
            state = auction_timers.get(room_code)
            if not isinstance(state, dict):
                break
            if not state.get("running", False):
                break
            
            secs = int(state.get("seconds_left", 1)) - 1
            state["seconds_left"] = secs
            socketio.emit("timer_tick", {"seconds_left": secs}, room=f"auction_{room_code}")
            
            if secs <= 0:
                state["running"] = False
                pid = state.get("player_id")
                with app.app_context():
                    resolve_player(room_code, pid)
                break

    socketio.start_background_task(countdown)


def resolve_player(room_code, player_id):
    """Resolve a player auction when timer expires."""
    player = Player.query.get(player_id)
    if not player:
        return

    highest_bid = Bid.query.filter_by(player_id=player_id).order_by(Bid.amount.desc()).first()
    room = f"auction_{room_code}"

    if highest_bid:
        # SOLD!
        team = Team.query.get(highest_bid.team_id)
        player.is_sold = True
        player.sold_price = highest_bid.amount
        player.team_id = highest_bid.team_id
        team.purse_remaining -= highest_bid.amount
        db.session.commit()

        socketio.emit("player_sold", {
            "player": get_player_data(player),
            "team": get_team_data(team),
            "sold_price": highest_bid.amount,
            "sold_price_formatted": format_price(highest_bid.amount),
        }, room=room)
    else:
        # UNSOLD
        player.is_unsold = True
        db.session.commit()

        socketio.emit("player_unsold", {
            "player": get_player_data(player),
        }, room=room)


@socketio.on("place_bid")
def handle_bid(data):
    room_code = data.get("room_code")
    team_id = data.get("team_id")
    auction = Auction.query.filter_by(room_code=room_code).first()
    if not auction or not auction.current_player_id:
        emit("error", {"message": "No active player"})
        return

    player = Player.query.get(auction.current_player_id)
    team = Team.query.get(team_id)
    if not player or not team:
        emit("error", {"message": "Invalid player or team"})
        return

    # Get current highest bid
    highest_bid = Bid.query.filter_by(player_id=player.id).order_by(Bid.amount.desc()).first()

    if highest_bid:
        if highest_bid.team_id == team_id:
            emit("error", {"message": "You already have the highest bid!"})
            return
        bid_amount = highest_bid.amount + get_bid_increment(highest_bid.amount)
    else:
        bid_amount = player.base_price

    # Check purse
    # Account for max players still needed (leave room for minimum bids)
    squad_count = Player.query.filter_by(team_id=team.id, is_sold=True).count()
    if squad_count >= 18:
        emit("error", {"message": "Squad is full (18 players)!"})
        return

    if bid_amount > team.purse_remaining:
        emit("error", {"message": "Insufficient purse!"})
        return

    # Place the bid
    bid = Bid(player_id=player.id, team_id=team.id, amount=bid_amount)
    db.session.add(bid)
    db.session.commit()

    next_bid = bid_amount + get_bid_increment(bid_amount)
    room = f"auction_{room_code}"

    # Reset timer to 7 seconds on new bid for rapid-fire auction
    if room_code in auction_timers:
        auction_timers[room_code]["seconds_left"] = 7

    # Broadcast the bid
    socketio.emit("bid_update", {
        "player_id": player.id,
        "team_id": team.id,
        "team_name": team.short_name,
        "team_color": team.color,
        "amount": bid_amount,
        "amount_formatted": format_price(bid_amount),
        "next_bid": next_bid,
        "next_bid_formatted": format_price(next_bid),
        "bidder_name": team.name,
    }, room=room)


@socketio.on("pause_auction")
def handle_pause(data):
    room_code = data.get("room_code")
    auction = Auction.query.filter_by(room_code=room_code).first()
    if auction:
        if room_code in auction_timers:
            auction_timers[room_code]["running"] = False
        auction.status = "paused"
        db.session.commit()
        emit("auction_paused", {}, room=f"auction_{room_code}")


@socketio.on("resume_auction")
def handle_resume(data):
    room_code = data.get("room_code")
    auction = Auction.query.filter_by(room_code=room_code).first()
    if auction and auction.current_player_id:
        auction.status = "live"
        db.session.commit()
        # Restart timer with remaining time
        state = auction_timers.get(room_code, {"seconds_left": 60})
        auction_timers[room_code] = {
            "seconds_left": state.get("seconds_left", 60),
            "running": True,
            "player_id": auction.current_player_id,
        }
        emit("auction_resumed", {"seconds_left": state.get("seconds_left", 60)}, room=f"auction_{room_code}")
        start_timer(room_code, auction.current_player_id)


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
