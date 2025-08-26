from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json

# FPL API Endpoints
FPL_API_URL_BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_API_URL_ENTRY = "https://fantasy.premierleague.com/api/entry/{}/"
FPL_API_URL_HISTORY = "https://fantasy.premierleague.com/api/entry/{}/history/"

def dashboard_view(request):
    # View này chỉ đơn giản là render template chính của bạn.
    return render(request, 'fantasy_dashboard.html')

# --- API VIEWS ---

def test_connection(request):
    try:
        response = requests.get(FPL_API_URL_BOOTSTRAP)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        current_gameweek = next((gw for gw in data['events'] if gw['is_current']), None)
        return JsonResponse({
            "success": True,
            "current_gameweek": current_gameweek['id'] if current_gameweek else 'N/A'
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({"success": False, "error": str(e)}, status=502)

@csrf_exempt
def add_manager(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            manager_ids = body.get('manager_ids')
            if not manager_ids or not isinstance(manager_ids, list):
                return JsonResponse({"success": False, "error": "A list of Manager IDs is required."}, status=400)

            added_managers = []
            failed_ids = []

            for manager_id in manager_ids:
                try:
                    # Basic validation to ensure it's a digit-based ID
                    if not str(manager_id).isdigit():
                        failed_ids.append({"id": manager_id, "reason": "ID không hợp lệ"})
                        continue

                    response = requests.get(FPL_API_URL_ENTRY.format(manager_id))
                    response.raise_for_status()
                    data = response.json()

                    manager_data = {
                        "id": data['id'],
                        "name": f"{data['player_first_name']} {data['player_last_name']}",
                        "team_name": data['name'],
                    }
                    added_managers.append(manager_data)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        failed_ids.append({"id": manager_id, "reason": "Không tồn tại"})
                    else:
                        failed_ids.append({"id": manager_id, "reason": "Lỗi API"})
                except Exception:
                    failed_ids.append({"id": manager_id, "reason": "Lỗi không xác định"})

            return JsonResponse({
                "success": True,
                "managers": added_managers,
                "failed": failed_ids
            })
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)


def get_manager_stats(request, manager_id):
    try:
        entry_res = requests.get(FPL_API_URL_ENTRY.format(manager_id))
        entry_res.raise_for_status()
        entry_data = entry_res.json()

        history_res = requests.get(FPL_API_URL_HISTORY.format(manager_id))
        history_res.raise_for_status()
        history_data = history_res.json()

        gameweek_points, total_points, highest_gw, lowest_gw = [], 0, None, None

        for gw in history_data.get('current', []):
            total_points = gw['total_points']
            gameweek_points.append({
                "gameweek": gw['event'], "points": gw['points'], "total_points": gw['total_points'],
                "rank": gw['rank'], "bank": gw['bank'] / 10.0, "value": gw['value'] / 10.0,
                "event_transfers": gw['event_transfers'], "event_transfers_cost": gw['event_transfers_cost'],
                "points_on_bench": gw['points_on_bench']
            })
            if not highest_gw or gw['points'] > highest_gw['points']: highest_gw = gw
            if not lowest_gw or gw['points'] < lowest_gw['points']: lowest_gw = gw
        
        gameweeks_played = len(gameweek_points)
        average_points = round(total_points / gameweeks_played) if gameweeks_played > 0 else 0

        stats = {
            "manager_info": {"player_first_name": entry_data['player_first_name'], "player_last_name": entry_data['player_last_name'], "name": entry_data['name']},
            "total_points": total_points, "average_points": average_points,
            "highest_gameweek": highest_gw, "lowest_gameweek": lowest_gw,
            "gameweeks_played": gameweeks_played, "gameweek_points": gameweek_points
        }
        return JsonResponse({"success": True, "data": stats})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@csrf_exempt
def compare_managers(request):
    if request.method == 'POST':
        try:
            manager_ids = json.loads(request.body).get('manager_ids', [])
            all_managers_data = []
            for manager_id in manager_ids:
                entry_res = requests.get(FPL_API_URL_ENTRY.format(manager_id)); entry_res.raise_for_status(); entry_data = entry_res.json()
                history_res = requests.get(FPL_API_URL_HISTORY.format(manager_id)); history_res.raise_for_status(); history_data = history_res.json()
                all_managers_data.append({
                    "id": entry_data['id'], "name": f"{entry_data['player_first_name']} {entry_data['player_last_name']}",
                    "team_name": entry_data['name'], "total_points": entry_data['summary_overall_points'],
                    "gameweeks": [{"gameweek": gw['event'], "points": gw['points']} for gw in history_data.get('current', [])]
                })
            return JsonResponse({"success": True, "data": {"managers": all_managers_data}})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

@csrf_exempt
def remove_manager(request, manager_id):
    # This is now a placeholder, as the actual removal happens on the client-side.
    return JsonResponse({"success": True, "message": f"Manager {manager_id} removal acknowledged."})
