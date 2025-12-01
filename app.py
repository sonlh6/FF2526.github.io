from flask import Flask, render_template, jsonify, request, session
import requests
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FPLAPIError(Exception):
    """Lỗi cơ bản khi giao tiếp với FPL API."""
    pass

class ManagerNotFound(FPLAPIError):
    """Lỗi khi không tìm thấy manager ID."""
    pass


class FantasyAPI:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
    
    def get_live_event(self, gameweek: int) -> Dict:
        """Lấy dữ liệu live (điểm cầu thủ) cho toàn bộ gameweek."""
        url = f"{self.base_url}event/{gameweek}/live/"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_manager_info(self, manager_id: int) -> Dict:
        """Lấy thông tin manager. Ném ra ManagerNotFound hoặc FPLAPIError khi có lỗi."""
        try:
            url = f"{self.base_url}entry/{manager_id}/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ManagerNotFound(f"Manager {manager_id} not found") from e
            logger.error(f"HTTP Error getting manager info for {manager_id}: {e}")
            raise FPLAPIError(f"API error for manager {manager_id}") from e
        except Exception as e:
            logger.error(f"Error getting manager info for {manager_id}: {e}")
            raise FPLAPIError(f"Generic error for manager {manager_id}") from e
    
    def get_manager_history(self, manager_id: int) -> Dict:
        """Lấy lịch sử điểm của manager. Ném ra ManagerNotFound hoặc FPLAPIError khi có lỗi."""
        try:
            url = f"{self.base_url}entry/{manager_id}/history/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ManagerNotFound(f"History for manager {manager_id} not found") from e
            logger.error(f"HTTP Error getting manager history for {manager_id}: {e}")
            raise FPLAPIError(f"API error for manager history {manager_id}") from e
        except Exception as e:
            logger.error(f"Error getting manager history for {manager_id}: {e}")
            raise FPLAPIError(f"Generic error for manager history {manager_id}") from e
    
    def get_gameweek_picks(self, manager_id: int, gameweek: int) -> Dict:
        """Lấy đội hình của manager trong gameweek cụ thể. Ném ra FPLAPIError khi có lỗi."""
        try:
            url = f"{self.base_url}entry/{manager_id}/event/{gameweek}/picks/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting gameweek picks for manager {manager_id} GW {gameweek}: {e}")
            raise FPLAPIError(f"Could not get picks for manager {manager_id}") from e
    
    def get_league_standings(self, league_id: int) -> Dict:
        """Lấy bảng xếp hạng của league. Ném ra FPLAPIError khi có lỗi."""
        try:
            url = f"{self.base_url}leagues-classic/{league_id}/standings/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting league standings for {league_id}: {e}")
            raise FPLAPIError(f"Could not get standings for league {league_id}") from e
    
    def get_bootstrap_static(self) -> Dict:
        """Lấy dữ liệu cơ bản của game. Ném ra FPLAPIError khi có lỗi."""
        try:
            url = f"{self.base_url}bootstrap-static/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting bootstrap data: {e}")
            raise FPLAPIError("Could not get bootstrap data") from e

class FantasyStatsTracker:
    def __init__(self):
        self.api = FantasyAPI()
        self.managers_data = {}
        
    def add_manager(self, manager_id: int) -> bool:
        """Thêm manager vào danh sách theo dõi"""
        try:
            manager_info = self.api.get_manager_info(manager_id)
            self.managers_data[manager_id] = {
                'info': manager_info,
                'history': None,
                'last_updated': None
            }
            return True
        except (ManagerNotFound, FPLAPIError) as e:
            logger.error(f"Error adding manager {manager_id}: {e}")
            return False
    
    def update_manager_data(self, manager_id: int):
        """Cập nhật dữ liệu của manager. Ném ra exception khi có lỗi."""
        if manager_id not in self.managers_data:
            raise FPLAPIError(f"Attempted to update non-tracked manager {manager_id}")
        
        try:
            history = self.api.get_manager_history(manager_id)
            self.managers_data[manager_id]['history'] = history
            self.managers_data[manager_id]['last_updated'] = datetime.now()
        except (ManagerNotFound, FPLAPIError) as e:
            logger.error(f"Failed to update manager {manager_id}: {e}")
            self.managers_data[manager_id]['history'] = None
            raise # Ném lại lỗi để route có thể xử lý
    
    def get_manager_stats(self, manager_id: int) -> Optional[Dict]:
        """Lấy thống kê chi tiết của manager"""
        if manager_id not in self.managers_data:
            return None
        
        data = self.managers_data[manager_id]
        if not data['history']:
            return None
        
        history = data['history']
        current_season = history.get('current', [])
        
        if not current_season:
            return None
        
        # Tính toán các thống kê
        total_points = sum(gw['points'] for gw in current_season)
        gameweeks_played = len(current_season)
        avg_points = total_points / gameweeks_played if gameweeks_played > 0 else 0
        
        highest_gw = max(current_season, key=lambda x: x['points']) if current_season else None
        lowest_gw = min(current_season, key=lambda x: x['points']) if current_season else None
        
        # Điểm theo từng gameweek
        gameweek_points = [
            {
                'gameweek': gw['event'],
                'points': gw['points'],
                'total_points': gw['total_points'],
                'rank': gw['overall_rank'],
                'bank': gw['bank'] / 10,  # Convert to millions
                'value': gw['value'] / 10,
                'event_transfers': gw['event_transfers'],
                'event_transfers_cost': gw['event_transfers_cost'],
                'points_on_bench': gw['points_on_bench']
            }
            for gw in current_season
        ]
        
        return {
            'manager_info': data['info'],
            'total_points': total_points,
            'gameweeks_played': gameweeks_played,
            'average_points': round(avg_points, 1),
            'highest_gameweek': highest_gw,
            'lowest_gameweek': lowest_gw,
            'gameweek_points': gameweek_points,
            'last_updated': data['last_updated']
        }
    
    def compare_managers(self, manager_ids: List[int]) -> Dict:
        """So sánh nhiều managers"""
        comparison = {
            'managers': [],
            'gameweek_comparison': []
        }
        
        # Lấy data của các managers
        managers_stats = []
        for manager_id in manager_ids:
            stats = self.get_manager_stats(manager_id)
            if stats:
                managers_stats.append({
                    'id': manager_id,
                    'name': stats['manager_info']['player_first_name'] + ' ' + stats['manager_info']['player_last_name'],
                    'team_name': stats['manager_info']['name'],
                    'total_points': stats['total_points'],
                    'average_points': stats['average_points'],
                    'gameweeks': stats['gameweek_points']
                })
        
        comparison['managers'] = managers_stats
        
        # Tạo comparison theo gameweek
        if managers_stats:
            max_gameweeks = max(len(m['gameweeks']) for m in managers_stats)
            
            for gw in range(1, max_gameweeks + 1):
                gw_data = {'gameweek': gw, 'managers': []}
                
                for manager in managers_stats:
                    gw_points = next((g['points'] for g in manager['gameweeks'] if g['gameweek'] == gw), 0)
                    gw_total = next((g['total_points'] for g in manager['gameweeks'] if g['gameweek'] == gw), 0)
                    
                    gw_data['managers'].append({
                        'id': manager['id'],
                        'name': manager['name'],
                        'points': gw_points,
                        'total_points': gw_total
                    })
                
                comparison['gameweek_comparison'].append(gw_data)
        
        return comparison

# Khởi tạo tracker
tracker = FantasyStatsTracker()

@app.after_request
def add_no_cache_headers(response):
    """Thêm headers để ngăn trình duyệt cache các phản hồi API."""
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    """Trang chính"""
    return render_template('fantasy_dashboard.html', managers=[])

@app.route('/api/add-manager', methods=['POST'])
def add_manager():
    """API thêm manager"""
    try:
        data = request.json
        manager_id = int(data.get('manager_id', 0))
        
        if manager_id <= 0:
            return jsonify({'success': False, 'error': 'Manager ID không hợp lệ'})
        
        success = tracker.add_manager(manager_id)
        if success:
            # Update data ngay lập tức
            tracker.update_manager_data(manager_id)
            
            # Lưu vào session
            if 'managers' not in session:
                session['managers'] = []
            if manager_id not in session['managers']:
                session['managers'].append(manager_id)
            
            manager_info = tracker.managers_data[manager_id]['info']
            return jsonify({
                'success': True,
                'manager': {
                    'id': manager_id,
                    'name': f"{manager_info['player_first_name']} {manager_info['player_last_name']}",
                    'team_name': manager_info['name']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Không tìm thấy manager hoặc lỗi API'})
            
    except ValueError:
        return jsonify({'success': False, 'error': 'Manager ID phải là số'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/manager/<int:manager_id>/stats')
def get_manager_stats(manager_id):
    """API lấy thống kê manager"""
    try:
        if manager_id not in tracker.managers_data:
            if not tracker.add_manager(manager_id):
                return jsonify({'success': False, 'error': f'Manager ID {manager_id} không hợp lệ hoặc không tồn tại.'})

        # Update data trước khi lấy stats
        tracker.update_manager_data(manager_id)
        
        stats = tracker.get_manager_stats(manager_id)
        if stats:
            return jsonify({'success': True, 'data': stats})
        # Trường hợp này xảy ra nếu history có nhưng không có dữ liệu mùa giải 'current'
        return jsonify({'success': False, 'error': f'Không có dữ liệu mùa giải hiện tại cho manager {manager_id}.'})
    except ManagerNotFound as e:
        return jsonify({'success': False, 'error': f'Không tìm thấy dữ liệu cho manager {manager_id}. ID có thể không còn hợp lệ.'})
    except FPLAPIError as e:
        return jsonify({'success': False, 'error': f'Lỗi API khi tải dữ liệu cho manager {manager_id}. Vui lòng thử lại.'})
    except Exception as e:
        logger.exception(f"Lỗi không xác định khi lấy stats cho manager {manager_id}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/compare-managers', methods=['POST'])
def compare_managers():
    """API so sánh managers (có bổ sung live scores cho vòng hiện tại nếu chưa kết thúc)."""
    try:
        data = request.json
        manager_ids = [int(id) for id in data.get('manager_ids', [])]

        if not manager_ids:
            return jsonify({'success': False, 'error': 'Chưa chọn managers để so sánh'})

        # Update dữ liệu lịch sử cho các manager
        for manager_id in manager_ids:
            try:
                tracker.update_manager_data(manager_id)
            except (ManagerNotFound, FPLAPIError):
                logger.warning(f"Skipping manager {manager_id} in comparison due to update failure.")

        # Lấy dữ liệu so sánh cơ bản
        comparison = tracker.compare_managers(manager_ids)

        # Lấy thông tin gameweek hiện tại
        bootstrap_data = tracker.api.get_bootstrap_static()
        current_gw_info = next((gw for gw in bootstrap_data['events'] if gw['is_current']), None)

        current_gameweek = None
        current_gw_finished = True

        if current_gw_info:
            current_gameweek = current_gw_info['id']
            current_gw_finished = current_gw_info['finished']

            if not current_gw_finished:
                # --- Lấy dữ liệu live toàn bộ cầu thủ ---
                try:
                    live_data = tracker.api.get_live_event(current_gameweek)
                    elements_points = {
                        el['id']: el['stats']['total_points']
                        for el in live_data['elements']
                    }
                except Exception as e:
                    logger.error(f"Không thể lấy dữ liệu live event GW{current_gameweek}: {e}")
                    elements_points = {}

                # --- Tính điểm live cho từng manager ---
                for manager in comparison['managers']:
                    try:
                        picks = tracker.api.get_gameweek_picks(manager['id'], current_gameweek)
                        starting = [p for p in picks['picks'] if p['position'] <= 11]

                        live_points = 0
                        for p in starting:
                            player_id = p['element']
                            multiplier = p['multiplier']
                            live_points += elements_points.get(player_id, 0) * multiplier

                        # Cập nhật vào danh sách gameweeks
                        found_gw = False
                        for g in manager['gameweeks']:
                            if g['gameweek'] == current_gameweek:
                                g['points'] = live_points
                                g['total_points'] = manager['total_points'] + live_points
                                found_gw = True
                                break
                        if not found_gw:
                            manager['gameweeks'].append({
                                'gameweek': current_gameweek,
                                'points': live_points,
                                'total_points': manager['total_points'] + live_points
                            })

                        # Thêm field live_total_points
                        manager['live_total_points'] = manager['total_points'] + live_points

                    except Exception as e:
                        logger.warning(f"Không thể tính live points cho manager {manager['id']}: {e}")
                        manager['live_total_points'] = manager['total_points']

        return jsonify({
            'success': True,
            'data': comparison,
            'current_gameweek': current_gameweek,
            'current_gw_finished': current_gw_finished
        })

    except Exception as e:
        logger.exception("Lỗi không xác định trong compare_managers")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove-manager/<int:manager_id>', methods=['DELETE'])
def remove_manager(manager_id):
    """API xóa manager"""
    try:
        if manager_id in tracker.managers_data:
            del tracker.managers_data[manager_id]
        
        # Xóa khỏi session
        if 'managers' in session and manager_id in session['managers']:
            session['managers'].remove(manager_id)
            session.modified = True
        
        return jsonify({'success': True, 'message': 'Đã xóa manager'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/managers')
def get_managers():
    """API lấy danh sách managers đã thêm"""
    try:
        managers = []
        session_managers = session.get('managers', [])
        
        for manager_id in session_managers:
            if manager_id not in tracker.managers_data:
                # Nếu manager có trong session nhưng không có trong bộ nhớ của worker này, hãy thử thêm vào.
                tracker.add_manager(manager_id)
            if manager_id in tracker.managers_data:
                manager_info = tracker.managers_data[manager_id]['info']
                managers.append({
                    'id': manager_id,
                    'name': f"{manager_info['player_first_name']} {manager_info['player_last_name']}",
                    'team_name': manager_info['name'],
                    'last_updated': tracker.managers_data[manager_id]['last_updated'].isoformat() if tracker.managers_data[manager_id]['last_updated'] else None
                })
        
        return jsonify({'success': True, 'data': managers})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/league/<int:league_id>')
def get_league_standings(league_id):
    """API lấy bảng xếp hạng league"""
    try:
        standings = tracker.api.get_league_standings(league_id)
        return jsonify({'success': True, 'data': standings})
    except ManagerNotFound as e: # Giả sử API có thể ném lỗi này cho league
        return jsonify({'success': False, 'error': f'Không tìm thấy league {league_id}.'})
    except FPLAPIError as e:
        return jsonify({'success': False, 'error': f'Lỗi API khi tải dữ liệu league {league_id}.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/live-scores')
def get_live_scores():
    """API lấy điểm live của các managers cho gameweek hiện tại."""
    try:
        # 1. Lấy gameweek hiện tại
        bootstrap_data = tracker.api.get_bootstrap_static()
        current_gw_info = next((gw for gw in bootstrap_data['events'] if gw['is_current']), None)
        
        if not current_gw_info:
            # Nếu không có gw current, thử lấy gw finished cuối cùng
            finished_gws = [gw for gw in bootstrap_data['events'] if gw['finished']]
            if finished_gws:
                current_gw_info = max(finished_gws, key=lambda x: x['id'])
            else:
                 return jsonify({'success': False, 'error': 'Không tìm thấy gameweek nào.'})

        current_gameweek = current_gw_info['id']

        # 2. Lấy danh sách managers
        manager_ids = session.get('managers', [])
        if not manager_ids:
            return jsonify({'success': True, 'data': {'gameweek': current_gameweek, 'scores': []}})

        live_scores = []
        # 3. Lấy điểm live cho từng manager
        for manager_id in manager_ids:
            try:
                if manager_id not in tracker.managers_data:
                    tracker.add_manager(manager_id)

                picks_data = tracker.api.get_gameweek_picks(manager_id, current_gameweek)
                manager_info = tracker.managers_data.get(manager_id, {}).get('info', {})
                
                entry_history = picks_data.get('entry_history', {})
                live_scores.append({
                    'id': manager_id,
                    'name': f"{manager_info.get('player_first_name', '')} {manager_info.get('player_last_name', '')}".strip(),
                    'team_name': manager_info.get('name', 'N/A'),
                    'live_points': entry_history.get('points', 0),
                    'transfers_cost': entry_history.get('event_transfers_cost', 0)
                })
            except FPLAPIError as e:
                logger.warning(f"Could not fetch live score for manager {manager_id}: {e}")
                manager_info = tracker.managers_data.get(manager_id, {}).get('info', {})
                live_scores.append({
                    'id': manager_id,
                    'name': f"{manager_info.get('player_first_name', '')} {manager_info.get('player_last_name', '')}".strip() or f"Manager {manager_id}",
                    'team_name': manager_info.get('name', 'N/A'),
                    'live_points': 'Error',
                    'transfers_cost': 'N/A'
                })

        return jsonify({
            'success': True,
            'data': {
                'gameweek': current_gameweek,
                'scores': live_scores
            }
        })

    except FPLAPIError as e:
        return jsonify({'success': False, 'error': f'Lỗi API: {e}'})
    except Exception as e:
        logger.exception("Lỗi không xác định khi lấy live scores")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-connection')
def test_connection():
    """Test kết nối API"""
    try:
        bootstrap_data = tracker.api.get_bootstrap_static()
        current_gw = next((gw for gw in bootstrap_data['events'] if gw['is_current']), None)
        return jsonify({
            'success': True, 
            'message': 'Kết nối API thành công',
            'current_gameweek': current_gw['id'] if current_gw else 'N/A'
        })
    except FPLAPIError:
        return jsonify({'success': False, 'error': 'Không thể kết nối API'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)