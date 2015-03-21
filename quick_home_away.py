#!/usr/bin/python

from argparse import ArgumentParser
import json
import requests
import sys
import shelve
from pprint import pprint
from time import sleep
from datetime import datetime, timedelta, time

appKey = "I8U8uUExhEzXtPGxITMijwu2A5bgBf1X"
scope = "smartWrite"

def log( *args ):
    print datetime.now().strftime( "%Y-%m-%d %H:%M" ), " ".join( map( str, args ) )

class EcobeeApplication( object ):
    def __init__( self ):
        self.config = shelve.open( "ecobee.shelf" )
        # Assume somebody is home this many minutes after we saw somebody.
        self.homeDecayMinutes = 15
        # Map of thermostat ID to the last revision seen.
        self.lastSeen = {}

    def updateAuthentication( self, response ):
        assert response.ok
        result = response.json()

        self.config[ "access_token" ] = result[ "access_token" ]
        self.config[ "token_type" ] = result[ "token_type" ]
        self.config[ "refresh_token" ] = result[ "refresh_token" ]
        self.config[ "authentication_expiration" ] = datetime.now() + \
                timedelta( 0, 60 * int( result[ "expires_in" ] ) )

    def install( self ):
        r = requests.get(
                "https://api.ecobee.com/authorize?response_type=ecobeePin&client_id=%s&scope=%s"
                % ( appKey, scope ) )
        assert r.ok
        result = r.json()
        authorizationToken = result[ 'code' ]
        print "Please log onto the ecobee web portal, log in, select the menu "
        print "item in the top right (3 lines), and select MY APPS."
        print "Next, click Add Application and enter the following "
        print "authorization code:", result[ 'ecobeePin' ]
        print "Then follow the prompts to add the Quick Home/Away app."
        print "You have %d minutes." % result[ 'expires_in' ]
        print
        print "Hit enter when done:",
        raw_input()

        r = requests.post(
                "https://api.ecobee.com/token?grant_type=ecobeePin&code=%s&client_id=%s"
                % ( authorizationToken, appKey ) )
        self.updateAuthentication( r )

        print "Installation is complete. Now run this script without any "
        print "arguments to control your thermostat."

    def maybeRefreshAuthentication( self ):
        if "authentication_expiration" in self.config and \
                datetime.now() + timedelta( 0, 60 ) < self.config[ "authentication_expiration" ]:
            return
        log( "Refreshing authentication." )
        r = requests.post(
                "https://api.ecobee.com/token?grant_type=refresh_token&code=%s&client_id=%s"
                % ( self.config[ 'refresh_token' ], appKey ) )
        self.updateAuthentication( r )

    def get( self, call, args ):
        self.maybeRefreshAuthentication()
        r = requests.get(
                "https://api.ecobee.com/1/%s" % call,
                params={ 'json': json.dumps( args ) },
                headers={
                    'Content-Type': 'application/json;charset=UTF-8',
                    'Authorization': "%s %s" % ( self.config[ "token_type" ],
                        self.config[ "access_token" ] ) }
                )
        try:
            return r.json()
        except ValueError:
            log( "Couldn't decode:" )
            log( r.text )
            raise

    def post( self, call, args ):
        self.maybeRefreshAuthentication()
        r = requests.post(
                "https://api.ecobee.com/1/%s" % call,
                data=json.dumps( args ),
                headers={
                    'Content-Type': 'application/json;charset=UTF-8',
                    'Authorization': "%s %s" % ( self.config[ "token_type" ],
                        self.config[ "access_token" ] ) }
                )
        if not r.ok:
            log( r.text )
        assert r.ok
        return r.json()

    def thermostatSummary( self ):
        return self.get( "thermostatSummary", {
            "selection": {
                "selectionType": "registered",
                "selectionMatch": "",
                }
            } )

    def thermostat( self, identifiers, includeDevice=False, includeProgram=False,
            includeRuntime=False, includeEvents=False ):
        """Return the contents of thermostatList indexed by identifier."""
        data = self.get( "thermostat", {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": ":".join( identifiers ),
                "includeDevice": includeDevice,
                "includeProgram": includeProgram,
                "includeRuntime": includeRuntime,
                "includeEvents": includeEvents
                }
            } )
        return { thermostat[ 'identifier' ]: thermostat
                for thermostat in data[ 'thermostatList' ] }

    def runtimeReport( self, thermostatId, includeSensors=False ):
        start = datetime.now() - timedelta( 1 )
        end = datetime.now() + timedelta( 1 )
        return self.get( "runtimeReport",
                {
                "startDate": start.strftime( "%Y-%m-%d" ),
                "endDate": end.strftime( "%Y-%m-%d" ),
                #"columns": "",
                "includeSensors": includeSensors,
                "selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": thermostatId }
                } )

    def sensorReport( self, thermostatId ):
        result = self.runtimeReport( thermostatId, includeSensors=True )[
                'sensorList' ][ 0 ]
        sensors = {}
        for sensor in result[ 'sensors' ]:
            sensors[ sensor[ 'sensorId' ] ] = sensor
        columns = { name: index for index, name in enumerate( result[ 'columns' ] ) }
        data = []
        for row in result[ 'data' ]:
            parts = row.split( "," )
            dateString = "%s %s" % ( parts[ columns[ "date" ] ],
                    parts[ columns[ "time" ] ] )
            date = datetime.strptime( dateString, "%Y-%m-%d %H:%M:%S" )
            rowData = {}
            for sensor in sensors.itervalues():
                value = parts[ columns[ sensor[ "sensorId" ] ] ]
                if value in ( "", "null" ):
                    continue
                rowData.setdefault( sensor[ "sensorType" ], [] ).append( float( value ) )
            if rowData:
                data.append( ( date, rowData ) )
        return data

    def poll( self ):
        """Return a list of thermostat ids that have been updated since the
        last time we polled."""
        summary = self.thermostatSummary()
        updated = []
        if 'revisionList' not in summary:
            log( "WARNING: Couldn't find revisionList in the following summary object:" )
            pprint( summary )
            return []

        for revision in summary[ 'revisionList' ]:
            parts = revision.split( ":" )
            identifier = parts[ 0 ]
            name = parts[ 1 ]
            intervalRevision = parts[ 6 ]
            if intervalRevision != self.lastSeen.get( identifier ):
                updated.append( identifier )
                self.lastSeen[ identifier ] = intervalRevision
        return updated

    def aggressiveAway( self ):
        updated = self.poll()
        if not updated:
            return
        thermostat = self.thermostat( updated, includeEvents=True,
                includeProgram=True )
        for identifier in updated:
            data = self.sensorReport( identifier )
            sensorClimate = 'away'
            for date, sensorData in data[ -3: ]:
                occupied = sum( sensorData[ 'occupancy' ] )
                if occupied:
                    sensorClimate = 'home'
                log( date.strftime( "%H:%M" ),
                        ", ".join( "%s: %s" % ( k, v )
                            for k, v in sensorData.iteritems() ) )

            log( "Sensors say we're %s." % sensorClimate )

            runningClimateRef = None
            for event in thermostat[ identifier ][ 'events' ]:
                if event[ 'running' ]:
                    runningClimateRef = event[ 'holdClimateRef' ]
                    log( event[ 'type' ], event[ 'holdClimateRef' ],
                            "until", event[ 'endTime' ] )

            if runningClimateRef is None:
                # Maybe we're on the regular schedule
                runningClimateRef = thermostat[ identifier ][ 'program' ][
                        'currentClimateRef' ]
                log( "Regularly scheduled climate:", runningClimateRef )

            if runningClimateRef in ( 'home', 'away' ):
                if runningClimateRef != sensorClimate:
                    log( "Change climate from %s to %s" % ( runningClimateRef,
                            sensorClimate ) )
                    self.setHold( identifier, sensorClimate, 14 )

    def setHold( self, thermostatId, climate, minutes ):
        # Assume the thermostat is in the same timezone as this script.
        start = datetime.now()
        end = datetime.now() + timedelta( 0, minutes * 60 )
        self.post( "thermostat",
                {
                    "selection": {
                        "selectionType": "thermostats",
                        "selectionMatch": thermostatId
                        },
                    "functions": [
                        {
                            "type": "setHold",
                            "params": {
                                "holdClimateRef": climate,
                                "startDate": start.strftime( "%Y-%m-%d" ),
                                "startTime": start.strftime( "%H:%M:%S" ),
                                "endDate": end.strftime( "%Y-%m-%d" ),
                                "endTime": end.strftime( "%H:%M:%S" ),
                                "holdType": "dateTime",
                                #"coolHoldTemp": 780,  # Not used when setting holdClimateRef
                                #"heatHoldTemp": 700,  # Not used when setting holdClimateRef
                                }
                            }
                        ]
                    }
                )

    def thermostatIdentifiers( self ):
        identifiers = []
        for row in self.thermostatSummary()[ 'revisionList' ]:
            identifiers.append( row.split( ':' )[ 0 ] )
        return identifiers

    def sensors( self, thermostatId, sensorType ):
        result = self.get( "thermostat", {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": thermostatId,
                "includeDevice": True
                }
            } )
        sensors = []
        for thermostat in result[ 'thermostatList' ]:
            for device in thermostat[ 'devices' ]:
                for sensor in device[ 'sensors' ]:
                    if sensor[ 'type' ] == sensorType:
                        sensors.append( sensor )
        return sensors

def main():
    parser = ArgumentParser()
    parser.add_argument( "--install", action="store_true",
            help="Authorize this application to access your thermostat. "
            "Use this the first time you run the application." )
    parser.add_argument( "minutes", nargs='?', type=int,
            help="Run this many MINUTES and then exit. If this argument "
            "is omitted, run forever." )
    args = parser.parse_args()

    app = EcobeeApplication()

    if args.install:
        app.install()
        return

    if not args.minutes is None:
        endTime = datetime.now() + timedelta( 0, args.minutes * 60 )
        log( "Run until %s." % endTime )

    while True:
        nowTime = datetime.now().time()
        try:
            app.aggressiveAway()
        except Exception:
            import traceback
            traceback.print_exc()
        if not args.minutes is None and datetime.now() > endTime:
            break
        sleep( 60 - datetime.now().second )

sys.exit( main() )
