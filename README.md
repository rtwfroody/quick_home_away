# quick_home_away
This script will talk to an ecobee3 thermostat, acting like a more responsive
"smart home/away".

## Background

[ecobee][http://www.ecobee.com/]'s ecobee3 smart thermostat comes with several
sensors that allow it to figure out whether you're home or not. This combines
with a feature called Smart Home/Away which uses this information to not run
the heat/cooling when you're unexpectedly away, and to run it when you're
unexpectedly home.  This feature is very slow to react, though. It doesn't
declare you to be unexpectedly away until you've been gone for 2 hours.
Unexpectedly home is detected more quickly. I'm not sure what the exact timing
is.

This script does the same thing as Smart Home/Away, but tries to respond as
quickly as possible. It only applies when the schedule is set to home or away.
When that is the case, it will put in place a 14-minute hold for either home or
away, depending on what the occupancy sensors said for the last 15-minute
period.

Because all interaction with the thermostat goes through ecobee's servers,
there is still a fairly large delay between you coming home or leaving and the
thermostat being adjusted, but it's much less delay than using the Smart
Home/Away feature.

When you come home unexpectedly, it will take between 5 and 17 before the
thermostat is adjusted.

When you leave unexpectedly, it will take between 17 and 37 minutes before the
thermostat is adjusted.

I'm running this quite happily at home, and now when I leave for an hour the
thermostat actually goes down for a bit. My home has poor insulation, so this
translates to less time spent heating the house overall.

## Getting Started

Run "quick_home_away.py --install" and follow the prompts.

Now run quick_home_away.py with no arguments to put it in action.

## Compatibility

I developed this script under Linux, but it should work anywhere that Python
2.7 is available.
