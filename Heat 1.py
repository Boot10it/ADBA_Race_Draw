import random
teams=["Dragon 2","Dragon 1","Dragon 3","Dragon 4","Dragon 5","Dragon 6","Dragon 7","Dragon 8","Dragon 9","Dragon 10"]
print(teams)
# Shuffle the teams randomly
random.shuffle(teams)
number_lanes = int(input("How many lanes does the race have? "))

print(f"The race has {number_lanes} lanes.")
num_teams = len(teams)
print("Number of teams:", num_teams)
# Simple example of distributing teams into "races"
# This isn't the full solution, just a conceptual start
races_heat1 = []
current_race = []
for i, team in enumerate(teams):
    current_race.append(team)
    if len(current_race) == number_lanes:
        races_heat1.append(current_race)
        current_race = []
if current_race: # Add any remaining teams to the last race
    races_heat1.append(current_race)

print("\nHeat 1 (simplified):")
for i, race in enumerate(races_heat1):
    print(f"Race {i+1}: {race}")