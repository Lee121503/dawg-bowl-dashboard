import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Dawg Bowl Contest Dashboard", layout="wide")

# 🔀 Sidebar mode selector
mode = st.sidebar.selectbox("Choose Mode", ["Dashboard", "Elite Trait Scanner"])

# 🔹 Shared Uploads
st.sidebar.header("📥 Upload Contest Files")
uploaded_weeks = st.sidebar.file_uploader("Upload weekly CSVs", type="csv", accept_multiple_files=True)
uploaded_positions = st.sidebar.file_uploader("Upload Position List Excel", type=["xls", "xlsx"])

# 🔹 Dashboard Mode
if mode == "Dashboard":

    if uploaded_weeks and uploaded_positions:
        # 🔹 Load Contest Entries
        all_weeks = []
        for file in uploaded_weeks:
            week_label = file.name.split("_Week_")[1].split("_")[0]
            df = pd.read_csv(file)
            df["Week"] = f"Week {week_label}"
            all_weeks.append(df)
        entries_df = pd.concat(all_weeks, ignore_index=True)
# 🔹 Week Filter Setup
week_options = ["All Weeks"] + sorted(entries_df["Week"].unique())
selected_week = st.sidebar.selectbox("Filter by Week", week_options)

# 🔹 Apply Week Filter
filtered_df = entries_df.copy()
if selected_week != "All Weeks":
    filtered_df = filtered_df[filtered_df["Week"] == selected_week]


        # 🔹 Load Position List
        position_df = pd.read_excel(uploaded_positions)
        position_map = dict(zip(position_df["Name"], position_df["Position"]))

        # 🔹 Tag Player Positions
        for i in range(1, 7):
            col = f"Player {i}"
            pos_col = f"Pos {i}"
            entries_df[pos_col] = entries_df[col].map(position_map).fillna("Unknown")

        # 🔹 Assign Draft Roles
        def assign_roles(row):
            roles = {
                "QB Pick": None, "RB1 Pick": None, "WR1 Pick": None,
                "WR2 Pick": None, "TE Pick": None, "Flex Pick": None
            }
            rb_count = wr_count = 0
            used_slots = set()
            for i in range(1, 7):
                pos = row[f"Pos {i}"]
                slot = i
                if pos == "QB" and not roles["QB Pick"]:
                    roles["QB Pick"] = slot; used_slots.add(slot)
                elif pos == "RB" and rb_count < 1:
                    roles["RB1 Pick"] = slot; rb_count += 1; used_slots.add(slot)
                elif pos == "WR" and wr_count < 2:
                    if not roles["WR1 Pick"]: roles["WR1 Pick"] = slot
                    else: roles["WR2 Pick"] = slot
                    wr_count += 1; used_slots.add(slot)
                elif pos == "TE" and not roles["TE Pick"]:
                    roles["TE Pick"] = slot; used_slots.add(slot)
            for i in range(1, 7):
                pos = row[f"Pos {i}"]
                slot = i
                if slot not in used_slots and pos in ["RB", "WR", "TE"]:
                    roles["Flex Pick"] = slot
                    break
            return pd.Series(roles)

        entries_df = pd.concat([entries_df, entries_df.apply(assign_roles, axis=1)], axis=1)

        # 🔹 Entry Counts
        entries_df["Total Entries"] = entries_df.groupby("username")["username"].transform("count")

        # 🔹 Tag Percentile Tiers
        def tag_percentile_tiers(df):
            def tag_group(group):
                total = len(group)
                group["Top_0.1%"] = group["place"].astype(int) <= max(1, round(0.001 * total))
                group["Top_0.5%"] = group["place"].astype(int) <= max(1, round(0.005 * total))
                group["Top_1%"] = group["place"].astype(int) <= max(1, round(0.01 * total))
                return group
            return df.groupby("Week", group_keys=False).apply(tag_group)

        entries_df = tag_percentile_tiers(entries_df)

        # 🔹 Sidebar Filters
        st.sidebar.header("🔍 Filter Users")
        selected_user = st.sidebar.text_input("Username (optional)")
        min_entries = st.sidebar.slider("Minimum Entries", 0, int(entries_df["Total Entries"].max()), 0)
        sort_mode = st.sidebar.radio(
            "Sort by",
            ["Elite Finish Count", "Elite Finish Rate"]
        )


        # 🔹 Overall User Summary
        st.header("📊 User-Level Elite Finish Dashboard")

        user_summary = (
            filtered_df.groupby("username")[["Top_0.1%", "Top_0.5%", "Top_1%"]]
            .sum()
            .astype(int)
            .join(filtered_df["username"].value_counts().rename("Total Entries"))
            .reset_index()
            .rename(columns={"index": "username"})
        )
        
        # 🔹 Add rate columns
        user_summary["Top 0.1% Rate"] = user_summary["Top_0.1%"] / user_summary["Total Entries"]
        user_summary["Top 0.5% Rate"] = user_summary["Top_0.5%"] / user_summary["Total Entries"]
        user_summary["Top 1% Rate"] = user_summary["Top_1%"] / user_summary["Total Entries"]

        # 🔹 Apply filters
        filtered = user_summary[user_summary["Total Entries"] >= min_entries]
        if selected_user:
            filtered = filtered[filtered["username"].str.lower() == selected_user.lower()]

        # 🔹 Display with formatting
        if sort_mode == "Elite Finish Count":
            sort_cols = ["Top_0.1%", "Top_0.5%", "Top_1%"]
        else:
            sort_cols = ["Top 0.1% Rate", "Top 0.5% Rate", "Top 1% Rate"]

        st.dataframe(
            filtered.sort_values(by=sort_cols, ascending=False)
            .style.format({
                "Top 0.1% Rate": "{:.2%}",
                "Top 0.5% Rate": "{:.2%}",
                "Top 1% Rate": "{:.2%}"
            })
        )

        # 🔹 Export Button
        st.download_button("📤 Export Filtered Table", filtered.to_csv(index=False), "filtered_user_summary.csv")

        # 🔹 Weekly Draft Charts
        st.header("🎛️ Weekly Draft Position Charts")
        week_options = ["All Weeks"] + sorted(entries_df["Week"].unique())
        selected_week = st.selectbox("Select Week", week_options)

        if selected_week == "All Weeks":
            week_df = entries_df.copy()
            title_prefix = "All Weeks"
        else:
            week_df = entries_df[entries_df["Week"] == selected_week].copy()
            title_prefix = selected_week

        melted = week_df.melt(
            id_vars=["place", "Top_0.1%", "Top_0.5%", "Top_1%"],
            value_vars=[f"Pos {i}" for i in range(1, 7)],
            var_name="Round",
            value_name="Position"
        )
        melted["Round"] = melted["Round"].str.extract(r"(\d)").astype(int)

        def plot_tier(tier_label):
            tier_df = melted[melted[tier_label]]
            count_df = tier_df.groupby(["Round", "Position"]).size().reset_index(name="Count")
            pivot_df = count_df.pivot(index="Round", columns="Position", values="Count").fillna(0)
            fig, ax = plt.subplots(figsize=(10, 6))
            pivot_df.plot(kind="bar", stacked=False, ax=ax)
            ax.set_title(f"{title_prefix} — {tier_label} Draft Position Frequency")
            ax.set_xlabel("Draft Round")
            ax.set_ylabel("Count")
            ax.grid(axis="y")
            st.pyplot(fig)

        plot_tier("Top_0.1%")
        plot_tier("Top_0.5%")
        plot_tier("Top_1%")

        # 🔹 Individual User Breakdown
        st.header("🔍 Individual User Draft Breakdown")
        user_input = st.text_input("Enter username for breakdown")
        if user_input:
            user_df = entries_df[entries_df["username"].str.lower() == user_input.lower()]
            if not user_df.empty:
                st.subheader(f"📋 Summary for {user_input}")
                st.write(f"Total Entries: {len(user_df)}")
                st.write(f"Average Points: {user_df['points'].mean():.2f}")
                st.write(f"Top 0.1% Finishes: {user_df['Top_0.1%'].sum()}")
                st.write(f"Top 0.5% Finishes: {user_df['Top_0.5%'].sum()}")
                st.write(f"Top 1% Finishes: {user_df['Top_1%'].sum()}")
                st.dataframe(user_df[[
                    "Week", "place", "points",
                    "QB Pick", "RB1 Pick", "WR1 Pick", "WR2 Pick", "TE Pick", "Flex Pick"
                ]].sort_values(by=["Week", "place"]))
            else:
                st.warning("No entries found for that username.")

def run_trait_scanner(uploaded_files):
    st.title("🏆 Top 1% Draft Trait Scanner (By Week)")

    if not uploaded_files:
        st.info("📥 Please upload contest CSVs in the Dashboard tab first.")
        return

    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            week_label = file.name.split("_Week_")[1].split("_")[0]
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
            continue

        total_entries = len(df)
        top_cutoff = max(1, int(total_entries * 0.01))
        top_df = df.nsmallest(top_cutoff, "place")

        st.subheader(f"📅 Week {week_label}")
        st.markdown(f"**Total Entries:** {total_entries}  \n**Top 1% Cutoff:** Top {top_cutoff} entries")

        all_players = pd.melt(
            df,
            id_vars=["place"],
            value_vars=[f"Player {i}" for i in range(1, 7)],
            var_name="Slot",
            value_name="Player"
        )
        top_players = pd.melt(
            top_df,
            id_vars=["place"],
            value_vars=[f"Player {i}" for i in range(1, 7)],
            var_name="Slot",
            value_name="Player"
        )

        player_counts = all_players["Player"].value_counts().rename("All Entries")
        top_counts = top_players["Player"].value_counts().rename("Top 1%")

        trait_df = pd.concat([top_counts, player_counts], axis=1).fillna(0)
        trait_df["Elite Hit Rate (%)"] = (trait_df["Top 1%"] / trait_df["All Entries"]) * 100
        trait_df = trait_df.sort_values("Elite Hit Rate (%)", ascending=False)

        st.dataframe(trait_df.style.format({"Elite Hit Rate (%)": "{:.2f}"}))

    st.subheader("🔗 High-Impact Player Combos (Coming Soon)")
    st.markdown("Want to detect elite stacks or synergistic pairings? I’ll help you build that next.")


# 🔹 Trait Scanner Mode Trigger
if mode == "Elite Trait Scanner":
    run_trait_scanner(uploaded_weeks)
