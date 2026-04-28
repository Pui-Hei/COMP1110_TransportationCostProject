import os
import sys
import CSV_to_SQL
import SQL_Data_Retriever
import Transportation_Path_Calculation

def print_menu():
    print("\n" + "="*40)
    print("      TRANSPORTATION NETWORK MENU      ")
    print("="*40)
    print("1. Load networks (Import Map Data)")
    print("2. Show network summary (List Maps)")
    print("3. List all stops (Map Landmarks)")
    print("4. Query journeys (Find Best Path)")
    print("5. Exit")
    print("="*40)

def load_networks():
    print("\n--- Load Networks ---")
    try:
        map_id_str = input("Enter Map ID (integer): ").strip()
        if not map_id_str:
            print("Error: Map ID is required.")
            return
        try:
            map_id = int(map_id_str)
        except ValueError:
            print("Error: Map ID must be a valid integer.")
            return
        
        map_name = input("Enter Map Name: ").strip()
        if not map_name:
            print("Error: Map Name is required.")
            return

        print("\nPlease provide the file paths for the CSV files.")
        train_lines_path = input("Train Lines CSV path: ").strip()
        train_fees_path = input("Train Fees CSV path: ").strip()
        landmarks_path = input("Landmarks CSV path: ").strip()
        bus_lines_path = input("Bus Lines CSV path: ").strip()

        # Check if files exist before opening
        for path in [train_lines_path, train_fees_path, landmarks_path, bus_lines_path]:
            if not os.path.isfile(path):
                print(f"Error: File not found at '{path}'")
                return

        # Open files and pass them to the CSV_to_SQL module
        with open(train_lines_path, 'r', encoding='utf-8') as tl_file, \
             open(train_fees_path, 'r', encoding='utf-8') as tf_file, \
             open(landmarks_path, 'r', encoding='utf-8') as lm_file, \
             open(bus_lines_path, 'r', encoding='utf-8') as bl_file:
            
            print("\nProcessing and inserting map data... Please wait.")
            result = CSV_to_SQL.insert_map_data(
                map_id=map_id,
                map_name=map_name,
                train_lines_file=tl_file,
                train_fees_file=tf_file,
                landmarks_file=lm_file,
                bus_lines_file=bl_file
            )

        if result.get("success"):
            print("\nSuccess! Map data loaded.")
            print(f"Inserted Landmarks: {result.get('inserted_landmarks')}")
            print(f"Inserted Train Lines: {result.get('inserted_train_lines')}")
            print(f"Inserted Bus Lines: {result.get('inserted_bus_lines')}")
        else:
            print(f"\nFailed to load network: {result.get('error')}")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def show_network_summary():
    print("\n--- Network Summary ---")
    result = SQL_Data_Retriever.get_all_maps()
    
    if result.get("success"):
        maps = result.get("maps", [])
        if not maps:
            print("No networks (maps) found in the database.")
        else:
            print(f"Found {len(maps)} network(s):")
            for m in maps:
                print(f" - ID: {m['map_id']} | Name: {m['map_name']}")
    else:
        print(f"Error retrieving networks: {result.get('error')}")

def list_all_stops():
    print("\n--- List All Stops ---")
    try:
        map_id = int(input("Enter Map ID to list stops for: ").strip())
        result = SQL_Data_Retriever.get_map_landmarks(map_id)
        
        if result.get("success"):
            map_info = result.get("map", {})
            landmarks = result.get("landmarks", [])
            print(f"\nStops for Map: {map_info.get('map_name')} (ID: {map_id})")
            print(f"Total Stops: {len(landmarks)}")
            print("-" * 40)
            for lm in landmarks:
                abbr = f" ({lm['abbreviation']})" if lm.get('abbreviation') else ""
                print(f"[{lm['landmark_id']}] {lm['landmark_name']}{abbr} - {lm['type']}")
        else:
            print(f"Error: {result.get('error')}")
            
    except ValueError:
        print("Error: Map ID must be a valid integer.")

def query_journeys():
    print("\n--- Query Journeys ---")
    try:
        map_id_str = input("Enter Map ID: ").strip()
        if not map_id_str:
            print("Error: Map ID is required.")
            return
        try:
            map_id = int(map_id_str)
        except ValueError:
            print("Error: Map ID must be a valid integer.")
            return
        start_lm = input("Enter Start Landmark (Name or ID): ").strip()
        end_lm = input("Enter End Landmark (Name or ID): ").strip()
        
        transports_input = input("Enter available transports (comma-separated, e.g., train,bus,foot): ").strip()
        transports_available = [t.strip().lower() for t in transports_input.split(",") if t.strip()]
        
        element_to_optimize = input(
            "Optimize by (cheapest/fastest/least_transfer/fewest_segments) [default: fastest]: "
        ).strip().lower() or "fastest"
        algorithm_to_use = input("Algorithm (astar/greedy/dijkstra) [default: astar]: ").strip().lower() or "astar"
        
        max_walk_input = input("Max walk minutes [default: 15.0]: ").strip()
        if max_walk_input:
            try:
                max_walk_min = float(max_walk_input)
            except ValueError:
                print("Error: Max walk minutes must be a number.")
                return
        else:
            max_walk_min = 15.0

        top_k_input = input("Number of journeys to show [default: 3]: ").strip()
        if top_k_input:
            try:
                top_k = int(top_k_input)
            except ValueError:
                print("Error: Number of journeys must be a valid integer.")
                return
        else:
            top_k = None

        print("\nCalculating best path...")
        result = Transportation_Path_Calculation.get_best_path(
            map_id=map_id,
            start_lm=start_lm,
            end_lm=end_lm,
            transports_available=transports_available,
            element_to_optimize=element_to_optimize,
            algorithm_to_use=algorithm_to_use,
            max_walk_min=max_walk_min,
            top_k=top_k
        )

        if result.get("success"):
            data = result.get("data", {})
            print("\n=== JOURNEY RESULTS ===")
            print(f"From: {data.get('start_lm')} -> To: {data.get('end_lm')}")

            def print_journey(rank, path, summary):
                print(f"\nRank {rank}")
                print(f"Total Time: {summary.get('total_time_minutes')} mins")
                print(f"Total Cost: ${summary.get('total_cost')}")
                print(f"Segments: {summary.get('total_segments')}")
                print(f"Transfers: {summary.get('total_transfers')}")
                print(f"Walking time used: {summary.get('foot_minutes_used')} mins")
                print("Route:")
                for i, step in enumerate(path, 1):
                    print(
                        f"{i}. {step['start_point']} to {step['end_point']} "
                        f"via {step['transportation_method']} ({step['time_minutes']} mins)"
                    )

            primary_summary = data.get("summary", {})
            primary_path = data.get("path", [])
            print_journey(1, primary_path, primary_summary)

            alternatives = data.get("alternative_paths", [])
            for alt in alternatives:
                print_journey(alt.get("rank", "?"), alt.get("path", []), alt.get("summary", {}))
        else:
            print(f"\nError calculating journey: {result.get('error')}")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    while True:
        print_menu()
        choice = input("Select an option (1-5): ").strip()

        if choice == '1':
            load_networks()
        elif choice == '2':
            show_network_summary()
        elif choice == '3':
            list_all_stops()
        elif choice == '4':
            query_journeys()
        elif choice == '5':
            print("Exiting application. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    main()