# Comprehensive Feature Analysis for NBA Rebounding Prediction

## Executive Summary

This document provides a complete analysis of features for NBA rebounding prediction, including:
- **Missing features** that should be added
- **Optional features** that can enhance but aren't critical
- **Hidden gems** - small features that matter more than expected
- **Feature importance ranking** by category

---

## CURRENT FEATURE STATUS

### ✅ Currently Included:
- Rebounding metrics: TRB%, ORB%, DRB%, per-36 rates
- Team rebounding schemes: offensive/defensive rebounding philosophy
- Context features: rest days, back-to-backs, playoff context
- Matchup features: height/weight advantages, head-to-head stats
- Spatial features: zone preferences based on position

---

## 🔴 CRITICAL MISSING FEATURES

### 1. **Lineup Composition Features** (HIGHEST PRIORITY)
**Why Critical:** Who else is on the court directly affects rebounding opportunities.

**Features to Add:**
- **Teammate rebounding competition**: Sum of teammates' TRB% when player is on court
  - If playing with strong rebounders, fewer rebounds available
  - If playing with guards, more rebounds available
- **Opponent lineup rebounding strength**: Opponent's rebounding ability when player is on court
- **Lineup size**: Average height of lineup (big lineup = more rebounds)
- **Positional balance**: Number of bigs (C/PF) vs guards on court
- **Shared minutes**: How often player plays with specific teammates (affects chemistry)

**Implementation:**
```python
def _create_lineup_features(self, player_id, team_id, opponent_id, game_date):
    """Create lineup composition features."""
    features = pd.DataFrame()
    
    # Get typical lineup when player is on court
    lineup_data = self._get_player_lineup_data(player_id, game_date)
    
    # Teammate rebounding competition
    teammate_rebound_rates = [p['TRB%'] for p in lineup_data['teammates']]
    features['teammate_rebound_competition'] = sum(teammate_rebound_rates) / 100
    features['teammate_rebound_avg'] = np.mean(teammate_rebound_rates) / 100
    
    # Opponent rebounding strength
    opponent_rebound_rates = [p['TRB%'] for p in lineup_data['opponents']]
    features['opponent_rebound_strength'] = sum(opponent_rebound_rates) / 100
    
    # Lineup size (average height)
    teammate_heights = [self._height_to_inches(p['HEIGHT']) for p in lineup_data['teammates']]
    opponent_heights = [self._height_to_inches(p['HEIGHT']) for p in lineup_data['opponents']]
    features['lineup_height_advantage'] = np.mean(teammate_heights) - np.mean(opponent_heights)
    
    # Positional balance
    bigs_on_court = sum(1 for p in lineup_data['teammates'] if p['POSITION'] in ['C', 'PF'])
    features['bigs_on_court'] = bigs_on_court
    features['guards_on_court'] = 5 - bigs_on_court
    
    return features
```

---

### 2. **Shot Selection & Game Flow Features** (HIGH PRIORITY)
**Why Critical:** Shot type and game situation directly affect rebound opportunities.

**Features to Add:**
- **Team 3-point attempt rate**: More 3s = more long rebounds = different rebound patterns
- **Team shot selection profile**: % of shots from paint, mid-range, 3pt
- **Expected missed shots**: Based on team FG% and shot volume
- **Free throw rate**: High FT rate = fewer field goal attempts = fewer rebounds
- **Turnover rate**: More turnovers = fewer shots = fewer rebounds
- **Game pace mismatch**: Team pace vs opponent pace (affects total possessions)

**Implementation:**
```python
def _create_shot_selection_features(self, team_id, opponent_id, game_date):
    """Create shot selection and game flow features."""
    features = pd.DataFrame()
    
    # Team shot profile
    team_stats = self._get_team_stats(team_id, game_date)
    features['team_3pa_rate'] = team_stats['3PA'] / (team_stats['FGA'] + 1)
    features['team_paint_shot_rate'] = team_stats['PAINT_FGA'] / (team_stats['FGA'] + 1)
    features['team_mid_range_rate'] = 1 - features['team_3pa_rate'] - features['team_paint_shot_rate']
    
    # Expected missed shots
    features['team_fg_pct'] = team_stats['FG%'] / 100
    features['team_3p_pct'] = team_stats['3P%'] / 100
    features['expected_missed_2s'] = team_stats['FGA'] * (1 - features['team_3pa_rate']) * (1 - features['team_fg_pct'])
    features['expected_missed_3s'] = team_stats['FGA'] * features['team_3pa_rate'] * (1 - features['team_3p_pct'])
    features['total_expected_misses'] = features['expected_missed_2s'] + features['expected_missed_3s']
    
    # Free throw rate (fewer FGs = fewer rebounds)
    features['team_fta_rate'] = team_stats['FTA'] / (team_stats['FGA'] + team_stats['FTA'] + 1)
    
    # Turnover rate
    features['team_tov_rate'] = team_stats['TOV'] / (team_stats['POSS'] + 1)
    
    # Pace mismatch
    opp_stats = self._get_team_stats(opponent_id, game_date)
    features['pace_differential'] = team_stats['PACE'] - opp_stats['PACE']
    features['expected_possessions'] = (team_stats['PACE'] + opp_stats['PACE']) / 2
    
    return features
```

---

### 3. **Foul Trouble & Game Situation Features** (HIGH PRIORITY)
**Why Critical:** Fouls directly limit minutes, and game situation affects effort/rotation.

**Features to Add:**
- **Player foul rate**: Average fouls per game (predicts foul trouble risk)
- **Opponent foul drawing ability**: How often opponent gets opponent in foul trouble
- **Expected game situation**: Predicted score differential (blowout vs close)
- **Clutch game indicator**: Expected to be close in 4th quarter
- **Playoff intensity**: Playoff games have different effort levels

**Implementation:**
```python
def _create_foul_situation_features(self, player_id, opponent_id, game_date):
    """Create foul trouble and game situation features."""
    features = pd.DataFrame()
    
    # Player foul tendencies
    player_stats = self._get_player_stats(player_id, game_date)
    features['player_avg_fouls'] = player_stats['PF'] / player_stats['GP']
    features['player_foul_rate_per_36'] = (player_stats['PF'] / player_stats['MIN']) * 36
    
    # Opponent's ability to draw fouls
    opp_stats = self._get_team_stats(opponent_id, game_date)
    features['opponent_fta_rate'] = opp_stats['FTA'] / (opp_stats['FGA'] + opp_stats['FTA'] + 1)
    
    # Expected game situation (based on team strength)
    team_strength = self._get_team_strength(team_id, game_date)
    opp_strength = self._get_team_strength(opponent_id, game_date)
    features['expected_score_differential'] = team_strength - opp_strength
    features['expected_blowout'] = 1 if abs(features['expected_score_differential']) > 15 else 0
    features['expected_close_game'] = 1 if abs(features['expected_score_differential']) < 5 else 0
    
    return features
```

---

### 4. **Fatigue & Workload Features** (MEDIUM-HIGH PRIORITY)
**Why Critical:** Fatigue affects rebounding effort and positioning.

**Features to Add:**
- **Recent minutes workload**: Total minutes in last 3, 5, 7 games
- **Games played in last week**: Frequency of games
- **Travel distance**: Miles traveled for away games
- **Time zone changes**: Jet lag effect
- **Elevation changes**: Playing at altitude (Denver) affects fatigue
- **Season fatigue**: Games played in season (accumulated fatigue)

**Implementation:**
```python
def _create_fatigue_features(self, player_id, team_id, game_date):
    """Create fatigue and workload features."""
    features = pd.DataFrame()
    
    # Recent workload
    recent_games = self._get_recent_games(player_id, game_date, days=14)
    features['minutes_last_3_games'] = sum([g['MIN'] for g in recent_games[:3]])
    features['minutes_last_5_games'] = sum([g['MIN'] for g in recent_games[:5]])
    features['minutes_last_7_games'] = sum([g['MIN'] for g in recent_games[:7]])
    features['games_last_7_days'] = len([g for g in recent_games if (game_date - g['DATE']).days <= 7])
    
    # Travel
    if not game_data.get('IS_HOME'):
        travel = self._calculate_travel(team_id, game_date)
        features['travel_distance_miles'] = travel['distance']
        features['time_zone_change'] = travel['timezone_diff']
        features['elevation_change'] = travel['elevation_diff']
    else:
        features['travel_distance_miles'] = 0
        features['time_zone_change'] = 0
        features['elevation_change'] = 0
    
    # Season fatigue
    season_games = self._get_season_games_played(player_id, game_date)
    features['games_played_this_season'] = season_games
    features['season_fatigue_factor'] = min(season_games / 82, 1.0)  # Normalize to full season
    
    return features
```

---

## 🟡 OPTIONAL BUT VALUABLE FEATURES

### 5. **Advanced Rebounding Metrics** (If Available)
- **Contested rebound rate**: % of rebounds that were contested
- **Box out frequency**: How often player boxes out (if tracking data available)
- **Rebound positioning score**: Quality of positioning (if spatial data available)
- **Rebound conversion rate**: Rebounds per opportunity
- **Tip-out rate**: How often player tips rebounds to teammates

**Priority:** Medium - Nice to have if data available, but not critical.

---

### 6. **Coaching & System Features**
- **Coach rebounding emphasis**: Historical team rebounding rates under coach
- **Substitution patterns**: When player typically enters/exits (affects minutes)
- **Small ball vs traditional**: Team's typical lineup size
- **Defensive scheme**: Zone vs man (affects rebounding positioning)

**Priority:** Medium - Can be inferred from team stats, but explicit features help.

**Implementation:**
```python
def _create_coaching_features(self, team_id, game_date):
    """Create coaching and system features."""
    features = pd.DataFrame()
    
    # Coach's historical rebounding emphasis
    coach_id = self._get_team_coach(team_id, game_date)
    coach_stats = self._get_coach_rebounding_stats(coach_id, game_date)
    features['coach_orb_emphasis'] = coach_stats['avg_orb_pct']
    features['coach_drb_emphasis'] = coach_stats['avg_drb_pct']
    
    # Team's typical lineup size
    lineup_data = self._get_team_lineup_data(team_id, game_date)
    features['avg_lineup_height'] = np.mean([self._height_to_inches(p['HEIGHT']) for p in lineup_data])
    features['small_ball_frequency'] = sum(1 for l in lineup_data if l['avg_height'] < 78) / len(lineup_data)
    
    return features
```

---

### 7. **Player-Specific Advanced Features**
- **Age/experience**: Veterans may position better
- **Contract year**: Players in contract years may try harder
- **Injury history**: Players coming off injuries may be limited
- **Playing style**: Some players are better at positioning (box out specialists)
- **Clutch performance**: How player performs in close games

**Priority:** Low-Medium - Can help but may not be major factors.

---

## 💎 HIDDEN GEMS - Small Features That Matter More Than Expected

### 8. **Expected Rebound Opportunities (Not Just Missed Shots)**
**Why It Matters:** Not all missed shots create equal rebound opportunities.

**Features:**
- **Shot distance**: Longer shots = longer rebounds = different patterns
- **Shot type**: Layups vs jump shots (layups often bounce differently)
- **Shot clock**: Late clock shots often rushed = more misses = more rebounds
- **Fast break vs half-court**: Fast breaks = fewer rebounds (made shots or no rebound)

**Implementation:**
```python
def _create_rebound_opportunity_features(self, team_id, opponent_id, game_date):
    """Create detailed rebound opportunity features."""
    features = pd.DataFrame()
    
    # Shot distance distribution
    shot_chart = self._get_team_shot_chart(team_id, game_date)
    features['avg_shot_distance'] = np.mean([s['DISTANCE'] for s in shot_chart])
    features['paint_shot_pct'] = sum(1 for s in shot_chart if s['DISTANCE'] < 8) / len(shot_chart)
    features['long_shot_pct'] = sum(1 for s in shot_chart if s['DISTANCE'] > 20) / len(shot_chart)
    
    # Fast break rate
    play_by_play = self._get_play_by_play(team_id, game_date)
    fast_breaks = sum(1 for p in play_by_play if p['FAST_BREAK'])
    features['fast_break_rate'] = fast_breaks / len(play_by_play)
    
    # Shot clock usage
    features['avg_shot_clock'] = np.mean([p['SHOT_CLOCK'] for p in play_by_play if p['SHOT_CLOCK']])
    features['late_clock_shots_pct'] = sum(1 for p in play_by_play if p['SHOT_CLOCK'] < 5) / len(play_by_play)
    
    return features
```

---

### 9. **Momentum & Form Features**
**Why It Matters:** Recent performance trends can be more predictive than season averages.

**Features:**
- **Rebound momentum**: Last 3 games vs last 10 games (is player improving?)
- **Minutes trend**: Increasing or decreasing minutes (affects opportunity)
- **Consistency**: Standard deviation of rebounds (predictable vs volatile)
- **Hot/cold streaks**: Consecutive games above/below average

**Implementation:**
```python
def _create_momentum_features(self, player_id, game_date):
    """Create momentum and form features."""
    features = pd.DataFrame()
    
    recent_games = self._get_recent_games(player_id, game_date, n_games=10)
    rebounds = [g['REB'] for g in recent_games]
    minutes = [g['MIN'] for g in recent_games]
    
    if len(rebounds) >= 3:
        # Momentum: recent vs older
        last_3_rebounds = np.mean(rebounds[:3])
        last_10_rebounds = np.mean(rebounds)
        features['rebound_momentum'] = (last_3_rebounds - last_10_rebounds) / max(last_10_rebounds, 1)
        
        # Consistency
        features['rebound_consistency'] = 1 / (np.std(rebounds) + 1)  # Higher = more consistent
        
        # Streaks
        avg_rebounds = np.mean(rebounds)
        above_avg_streak = 0
        for r in rebounds:
            if r > avg_rebounds:
                above_avg_streak += 1
            else:
                break
        features['current_above_avg_streak'] = above_avg_streak
    
    # Minutes trend
    if len(minutes) >= 5:
        recent_minutes = np.mean(minutes[:3])
        older_minutes = np.mean(minutes[3:])
        features['minutes_trend'] = (recent_minutes - older_minutes) / max(older_minutes, 1)
    
    return features
```

---

### 10. **Opponent-Specific Matchup Features**
**Why It Matters:** Some players struggle against specific opponents or play styles.

**Features:**
- **Individual matchup history**: How player performs vs specific opponent players
- **Opponent defensive scheme**: How opponent defends player's position
- **Opponent rebounding style**: Aggressive vs conservative rebounding
- **Opponent pace**: Fast vs slow pace affects opportunities

**Implementation:**
```python
def _create_individual_matchup_features(self, player_id, opponent_id, game_date):
    """Create individual player-opponent matchup features."""
    features = pd.DataFrame()
    
    # Get likely defensive matchup
    likely_defender = self._predict_defensive_matchup(player_id, opponent_id, game_date)
    
    if likely_defender:
        # Head-to-head vs this specific defender
        h2h = self._get_player_vs_player_stats(player_id, likely_defender['PLAYER_ID'], game_date)
        if h2h:
            features['h2h_vs_defender_rebounds'] = h2h['avg_rebounds']
            features['h2h_vs_defender_minutes'] = h2h['avg_minutes']
        
        # Defender's rebounding ability (competition)
        features['defender_rebound_rate'] = likely_defender['TRB%'] / 100
        features['defender_height'] = self._height_to_inches(likely_defender['HEIGHT'])
        features['defender_weight'] = likely_defender['WEIGHT']
    
    # Opponent's defensive scheme vs player's position
    player_position = self._get_player_position(player_id)
    opp_scheme = self._get_opponent_defensive_scheme(opponent_id, player_position, game_date)
    features['opponent_doubles_position'] = 1 if opp_scheme.get('doubles', False) else 0
    features['opponent_switches_on_position'] = 1 if opp_scheme.get('switches', False) else 0
    
    return features
```

---

### 11. **Game Flow Prediction Features**
**Why It Matters:** Blowouts vs close games affect minutes and effort.

**Features:**
- **Expected game pace**: Based on team pace and opponent pace
- **Expected score**: Based on team strength (predicts blowout vs close)
- **Expected minutes**: Based on game situation (blowout = bench players)
- **Playoff vs regular season**: Different intensity

**Implementation:**
```python
def _create_game_flow_features(self, team_id, opponent_id, game_date, is_home):
    """Create game flow prediction features."""
    features = pd.DataFrame()
    
    # Team strength
    team_strength = self._get_team_strength(team_id, game_date)
    opp_strength = self._get_team_strength(opponent_id, game_date)
    
    # Expected score differential
    home_advantage = 3 if is_home else -3
    features['expected_score_differential'] = (team_strength - opp_strength) + home_advantage
    
    # Expected game type
    features['expected_blowout'] = 1 if abs(features['expected_score_differential']) > 15 else 0
    features['expected_close_game'] = 1 if abs(features['expected_score_differential']) < 5 else 0
    
    # Expected pace
    team_pace = self._get_team_pace(team_id, game_date)
    opp_pace = self._get_team_pace(opponent_id, game_date)
    features['expected_pace'] = (team_pace + opp_pace) / 2
    
    # Expected total possessions (more possessions = more rebounds)
    features['expected_possessions'] = features['expected_pace'] / 2
    
    return features
```

---

## 📊 FEATURE IMPORTANCE RANKING

### Tier 1: Critical (Must Have)
1. **Minutes prediction** (Layer 1) - Foundation
2. **Rebound opportunity prediction** (Layer 2) - Foundation
3. **Player rebounding rates** (TRB%, ORB%, DRB%) - Core skill
4. **Team rebounding schemes** - Context
5. **Opponent rebounding defense** - Context
6. **Lineup composition** - Direct impact on opportunities
7. **Shot selection profile** - Affects rebound patterns

### Tier 2: High Value (Should Have)
8. **Recent form/momentum** - Better than season averages
9. **Foul trouble risk** - Affects minutes
10. **Game situation** (blowout vs close) - Affects minutes/effort
11. **Fatigue/workload** - Affects effort
12. **Matchup features** (height, weight, H2H) - Individual matchups

### Tier 3: Medium Value (Nice to Have)
13. **Spatial/zone features** - If data available
14. **Coaching features** - System effects
15. **Advanced rebounding metrics** - If available
16. **Travel/fatigue details** - Refinement

### Tier 4: Low Value (Optional)
17. **Player age/experience** - Minor factor
18. **Contract year** - Minor motivation factor
19. **Clutch performance** - Situation-dependent

---

## 🎯 RECOMMENDED FEATURE ADDITIONS

### Immediate Additions (Before Training):
1. ✅ **Lineup composition features** - Critical for opportunity prediction
2. ✅ **Shot selection features** - Affects rebound patterns
3. ✅ **Foul trouble features** - Affects minutes
4. ✅ **Momentum/form features** - Better than static averages
5. ✅ **Game flow features** - Affects minutes and effort

### Phase 2 Additions (After Initial Model):
6. **Advanced matchup features** - Individual player matchups
7. **Coaching features** - System effects
8. **Fatigue details** - Travel, elevation, etc.

### Phase 3 Additions (If Data Available):
9. **Spatial tracking features** - If player tracking data available
10. **Advanced rebounding metrics** - Contested rebounds, box outs, etc.

---

## 🔧 IMPLEMENTATION PRIORITY

### Week 1: Core Features
- Lineup composition
- Shot selection
- Foul trouble
- Momentum/form

### Week 2: Context Features
- Game flow prediction
- Fatigue/workload
- Advanced matchup

### Week 3: Polish
- Coaching features
- Travel details
- Advanced metrics (if available)

---

## 📝 FEATURE CHECKLIST

### Player Features
- [x] TRB%, ORB%, DRB%
- [x] Per-36 rates
- [x] Recent form (last 5, 10 games)
- [x] Rebound trend (increasing/decreasing)
- [ ] **Momentum score** (recent vs older)
- [ ] **Consistency score** (std dev)
- [ ] **Foul rate** (predicts foul trouble)
- [ ] **Age/experience** (optional)

### Team Features
- [x] Team rebounding rates
- [x] Team rebounding philosophy
- [x] Team pace
- [ ] **Shot selection profile** (3PA rate, paint rate)
- [ ] **Free throw rate** (affects FG attempts)
- [ ] **Turnover rate** (affects shots)
- [ ] **Coaching emphasis** (optional)

### Opponent Features
- [x] Opponent rebounding defense
- [x] Opponent pace
- [ ] **Opponent shot selection** (affects rebound patterns)
- [ ] **Opponent foul drawing** (affects player fouls)
- [ ] **Opponent defensive scheme** (optional)

### Context Features
- [x] Home/away
- [x] Rest days
- [x] Back-to-back
- [x] Playoff vs regular season
- [ ] **Expected game situation** (blowout vs close)
- [ ] **Travel distance** (optional)
- [ ] **Time zone changes** (optional)
- [ ] **Elevation** (optional)

### Matchup Features
- [x] Height advantage
- [x] Weight advantage
- [x] Head-to-head stats
- [ ] **Individual defender matchup** (who guards player)
- [ ] **Lineup height advantage** (team vs team)
- [ ] **Positional balance** (bigs vs guards)

### Lineup Features
- [ ] **Teammate rebounding competition** (CRITICAL)
- [ ] **Opponent lineup rebounding strength** (CRITICAL)
- [ ] **Lineup size/average height**
- [ ] **Positional balance on court**

### Opportunity Features
- [x] Predicted minutes (Layer 1)
- [x] Predicted opportunities (Layer 2)
- [ ] **Expected missed shots** (based on FG%)
- [ ] **Shot distance distribution**
- [ ] **Fast break rate**
- [ ] **Shot clock usage**

### Spatial Features
- [x] Zone preferences (position-based)
- [ ] **Actual zone data** (if available)
- [ ] **Rebound hot spots** (if tracking data available)

---

## 🎓 KEY INSIGHTS

1. **Lineup composition is critical** - More important than individual player stats in many cases
2. **Momentum > averages** - Recent form often more predictive than season averages
3. **Shot selection matters** - 3-point heavy teams create different rebound patterns
4. **Game situation affects everything** - Blowouts change minutes, effort, rotations
5. **Foul trouble is predictable** - Player foul rates can predict minutes limits
6. **Fatigue accumulates** - Recent workload matters more than single-game rest
7. **Matchups matter at individual level** - Not just team vs team, but player vs defender

---

## 🚀 NEXT STEPS

1. **Implement Tier 1 features immediately** (lineup, shot selection, foul trouble)
2. **Add Tier 2 features** (momentum, game flow, fatigue)
3. **Test feature importance** using model feature_importances_
4. **Iterate based on results** - Remove low-importance features, add new ones
5. **Monitor feature stability** - Ensure features don't change meaning over time

---

This comprehensive feature analysis ensures you're capturing all important signals for accurate rebound prediction while avoiding feature bloat.

