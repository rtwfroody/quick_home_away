# quick_home_away
This script will talk to an ecobee3 thermostat, acting like a more responsive
"smart home/away".

## Background

[ecobee](http://www.ecobee.com/)'s ecobee3 smart thermostat comes with several
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

## Security

I got the following e-mail from developer@ecobee.com:
> We are really happy to see your use of the ecobee API to create your Quick
> Home/Away App, and it is great that you are sharing this knowledge publicly.
> One issue we noticed is that the code you posed on GitHub
> (https://github.com/rtwfroody/quick_home_away/blob/master/quick_home_away.py)
> exposes your own Application Key. This is supposed to be a closely guarded
> secret, as anyone else can now use this key and pose themselves as your app.
> It is best if you revoke the current app and regenerate a new key.

https://www.ecobee.com/home/developer/api/documentation/v1/auth/auth-intro.shtml
also contains this warning:
> You are ultimately responsible for your application key. It should never,
> under any circumstances be shared or given away. Should ecobee detect that an
> application key has been compromised, it will be revoked. Once this occurs
> all deployments of your application will stop working.

I am unsure how somebody else can use the app key to gain access to a
thermostat, and I'm also not sure how to release open source software while
keeping the app key secret. I replied to the e-mail asking about that but
have gotten no reply.

In the meantime, if you want to be paranoid, you can generate your own app key
by registering as a developer at https://www.ecobee.com/developers/ and then
Create New from the DEVELOPER menu in the Ecobee web interface for your
thermostat. Once that's done just change the appKey near the top of the script.
