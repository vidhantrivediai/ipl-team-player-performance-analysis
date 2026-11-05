import zipfile
from io import BytesIO
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="IPL Performance Analysis",
    page_icon="🏏",
    layout="wide"
)

st.title("🏏 IPL Team and Player Performance Analysis")
st.caption("Interactive IPL analytics dashboard")

def find_col(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None

def number_col(df, col):
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0)
    return pd.Series(0, index=df.index, dtype="float64")

st.sidebar.header("IPL Dataset")

try:
    matches = pd.read_csv("matches.csv")

    with zipfile.ZipFile("deliveries.zip") as zip_file:
        csv_files = [
            name for name in zip_file.namelist()
            if name.lower().endswith(".csv")
        ]

        if not csv_files:
            st.error("No CSV file found inside deliveries.zip")
            st.stop()

        with zip_file.open(csv_files[0]) as file:
            df = pd.read_csv(file)

    st.success("IPL datasets loaded successfully!")

except Exception as e:
    st.error(f"Dataset loading error: {e}")
    st.stop()

# Identify columns
season_col = find_col(matches, ["season", "Season", "year"])
winner_col = find_col(matches, ["winner", "Winner"])
team1_col = find_col(matches, ["team1", "Team1"])
team2_col = find_col(matches, ["team2", "Team2"])

batter_col = find_col(df, ["batter", "batsman"])
bowler_col = find_col(df, ["bowler"])
runs_col = find_col(df, ["batter_runs", "batsman_runs"])
total_runs_col = find_col(df, ["total_runs"])
wide_col = find_col(df, ["wide_runs"])
noball_col = find_col(df, ["noball_runs"])
bye_col = find_col(df, ["bye_runs"])
legbye_col = find_col(df, ["legbye_runs"])
penalty_col = find_col(df, ["penalty_runs"])
dismissal_col = find_col(df, ["dismissal_kind"])
player_out_col = find_col(df, ["player_dismissed"])

st.success("Both IPL datasets uploaded successfully!")

# Overview
st.header("📊 Dataset Overview")

c1, c2, c3 = st.columns(3)
c1.metric("Total Matches", len(matches))
c2.metric("Total Deliveries", len(df))

if batter_col:
    c3.metric("Total Batters", df[batter_col].nunique())
else:
    c3.metric("Total Batters", "N/A")

# Season filter

if season_col:
    seasons = sorted(matches[season_col].dropna().unique().tolist())
    selected_season = st.sidebar.selectbox(
        "Select Season",
        ["All Seasons"] + seasons
    )

    if selected_season != "All Seasons":
        selected_matches = matches[
            matches[season_col] == selected_season
        ].copy()

        match_id_col = find_col(matches, ["id", "match_id"])
        delivery_id_col = find_col(df, ["match_id", "id"])

        if match_id_col and delivery_id_col:
            selected_ids = selected_matches[match_id_col].unique()
            df_view = df[
                df[delivery_id_col].isin(selected_ids)
            ].copy()
        else:
            df_view = df.copy()
    else:
        selected_matches = matches.copy()
        df_view = df.copy()
else:
    selected_matches = matches.copy()
    df_view = df.copy()


# Team analysis
st.header("🏆 Team Performance Analysis")

if winner_col and team1_col and team2_col:
    played = pd.concat([
        selected_matches[team1_col],
        selected_matches[team2_col]
    ]).dropna().value_counts()

    wins = selected_matches[winner_col].dropna().value_counts()

    team_stats = pd.DataFrame({
        "Team": played.index,
        "Matches Played": played.values
    })

    team_stats["Wins"] = team_stats["Team"].map(wins).fillna(0)
    team_stats["Win Percentage"] = (
        team_stats["Wins"] / team_stats["Matches Played"] * 100
    ).round(2)

    team_stats = team_stats.sort_values(
        "Wins", ascending=False
    )

    st.dataframe(team_stats, use_container_width=True)

    fig = px.bar(
        team_stats,
        x="Team",
        y="Wins",
        color="Team",
        title="Total Wins by IPL Team"
    )
    st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        team_stats,
        x="Team",
        y="Win Percentage",
        color="Team",
        title="Team Win Percentage"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Team or winner columns were not found in matches.csv.")

# Season analysis
st.header("📅 Season-wise Analysis")

if season_col:
    season_data = (
        selected_matches.groupby(season_col)
        .size()
        .reset_index(name="Matches")
    )

    fig = px.line(
        season_data,
        x=season_col,
        y="Matches",
        markers=True,
        title="Matches Played by Season"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Season column is not available in matches.csv.")

# Batting analysis
st.header("🏏 Batting Performance")

if batter_col and runs_col:
    df_view["__runs"] = number_col(df_view, runs_col)
    df_view["__wide"] = number_col(df_view, wide_col)

    batting = df_view.groupby(batter_col).agg(
        Runs=("__runs", "sum"),
        Balls_Faced=("__wide", lambda x: (x == 0).sum())
    ).reset_index()

    # Recalculate balls faced accurately from delivery rows
    balls = df_view.assign(
        __ball_faced=(df_view["__wide"] == 0).astype(int)
    ).groupby(batter_col)["__ball_faced"].sum()

    batting["Balls Faced"] = batting[batter_col].map(balls)
    batting["Strike Rate"] = (
        batting["Runs"] / batting["Balls Faced"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    batting = batting.sort_values("Runs", ascending=False)

    st.subheader("Top 10 Batsmen")
    st.dataframe(
        batting[["batter" if batter_col == "batter" else "batsman"
                 if batter_col == "batsman" else batter_col,
                 "Runs", "Balls Faced", "Strike Rate"]].head(10),
        use_container_width=True
    )

    fig = px.bar(
        batting.head(10),
        x=batter_col,
        y="Runs",
        color="Runs",
        title="Top 10 Batsmen by Runs"
    )
    st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        batting.head(10),
        x=batter_col,
        y="Strike Rate",
        color="Strike Rate",
        title="Top 10 Batsmen by Strike Rate"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Batter or batter-runs column not found.")

# Bowling analysis
st.header("🎯 Bowling Performance")

if bowler_col and total_runs_col:
    df_view["__total"] = number_col(df_view, total_runs_col)
    df_view["__bye"] = number_col(df_view, bye_col)
    df_view["__legbye"] = number_col(df_view, legbye_col)
    df_view["__penalty"] = number_col(df_view, penalty_col)
    df_view["__wide"] = number_col(df_view, wide_col)
    df_view["__noball"] = number_col(df_view, noball_col)

    # Runs charged to bowler exclude byes, leg byes and penalty runs
    df_view["__conceded"] = (
        df_view["__total"] - df_view["__bye"]
        - df_view["__legbye"] - df_view["__penalty"]
    )

    # Legal balls exclude wides and no-balls
    df_view["__legal_ball"] = (
        (df_view["__wide"] == 0) &
        (df_view["__noball"] == 0)
    ).astype(int)

    bowling = df_view.groupby(bowler_col).agg(
        Runs_Conceded=("__conceded", "sum"),
        Legal_Balls=("__legal_ball", "sum")
    ).reset_index()

    if dismissal_col:
        excluded = [
            "run out", "retired hurt", "retired out",
            "obstructing the field"
        ]
        wickets_df = df_view[
            df_view[dismissal_col].notna() &
            (~df_view[dismissal_col].astype(str).str.lower().isin(excluded))
        ]
        wickets = wickets_df[bowler_col].value_counts()
    elif player_out_col:
        wickets = df_view[
            df_view[player_out_col].notna()
        ][bowler_col].value_counts()
    else:
        wickets = pd.Series(dtype="int64")

    bowling["Wickets"] = bowling[bowler_col].map(wickets).fillna(0)
    bowling["Overs"] = (bowling["Legal_Balls"] / 6).round(1)
    bowling["Economy"] = (
        bowling["Runs_Conceded"] /
        (bowling["Legal_Balls"] / 6).replace(0, pd.NA)
    ).fillna(0).round(2)

    bowling = bowling.sort_values(
        ["Wickets", "Economy"], ascending=[False, True]
    )

    st.subheader("Top 10 Bowlers")
    st.dataframe(
        bowling[[bowler_col, "Wickets", "Overs",
                 "Runs_Conceded", "Economy"]].head(10),
        use_container_width=True
    )

    fig = px.bar(
        bowling.head(10),
        x=bowler_col,
        y="Wickets",
        color="Wickets",
        title="Top 10 Bowlers by Wickets"
    )
    st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        bowling.sort_values("Economy").head(10),
        x=bowler_col,
        y="Economy",
        color="Economy",
        title="10 Best Economy Rates (minimum overs not applied)"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Bowler or total-runs column not found.")

# Dataset preview
st.header("📁 Dataset Preview")

with st.expander("View Matches Dataset"):
    st.dataframe(selected_matches.head(20), use_container_width=True)

with st.expander("View Deliveries Dataset"):
    st.dataframe(df_view.head(20), use_container_width=True)

st.caption("IPL Performance Analysis | BCA AI Project")
