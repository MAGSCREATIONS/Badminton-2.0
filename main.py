from logic import load_players, add_player, remove_player, generate_balanced_groups

def show_players():
    """Displays the persistent roster saved in the JSON file."""
    players = load_players()
    if not players:
        print("\nNo players in the roster.")
        return
    print("\n--- Current Roster ---")
    for i, p in enumerate(players, 1):
        # Displays name and skill level matching the UI badges (ADV, INT, BEG)
        print(f"{i}. {p.get_name()} [{p.get_skill_level().value}]")

def main():
    while True:
        print("\n=== Badminton Manager CLI ===")
        print("1. Show Roster")
        print("2. Add Player (to persistent roster)")
        print("3. Remove Player")
        print("4. Generate Balanced Groups (Select Present Players)")
        print("5. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            show_players()

        elif choice == "2":
            name = input("Enter name: ")
            print("Skills: Beginner, Intermediate, Advanced")
            skill = input("Enter skill level: ")
            try:
                add_player(name, skill)
                print(f"Added {name} to the roster.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "3":
            name = input("Enter name to remove: ")
            remove_player(name)
            print(f"Removed {name} from the roster.")

        elif choice == "4":
            players = load_players()
            if len(players) < 4:
                print("Error: You need at least 4 players in the roster.")
                continue

            print("\nSelect present players (comma-separated numbers, e.g., 1,2,3,5):")
            for i, p in enumerate(players, 1):
                print(f"{i}. {p.get_name()}")
            
            selection = input("Present players: ")
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(",")]
                present_names = [players[i].get_name() for i in indices]
                
                # Calls the same logic the web app uses
                groups = generate_balanced_groups(present_names)
                
                for g in groups:
                    print(f"\n--- Court {g.get_group_number()} ---")
                    print(f"  Team A: {', '.join([p.get_name() for p in g.get_team1().get_players()])}")
                    print(f"  Team B: {', '.join([p.get_name() for p in g.get_team2().get_players()])}")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "5":
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()