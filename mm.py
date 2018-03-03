import requests
import time
from pprint import pprint
from datetime import datetime
import credentials

# start cron job at 7:15AM
WAIT_UNTIL_T_TIME = 2 #75*60 # app pauses after rain detected (75 minutes, until 8:30AM)
APP_RUN_TIME = 45*60 # run time (45 minutes, until 9:15AM)

# end points
WEATHER_CONDITIONS_ENDPOINT = credentials.WEATHER_CONDITIONS_ENDPOINT
WEATHER_HOURLY_ENDPOINT = credentials.WEATHER_HOURLY_ENDPOINT
MBTA_ENDPOINT = "http://realtime.mbta.com/developer/api/v2/predictionsbystop"
IFTTT_ENDPOINT = credentials.IFTTT_ENDPOINT

# mbta API info
MBTA_FORMAT = "json"
MBTA_TOKEN = credentials.MBTA_TOKEN

# my info
MY_NAME = "Raph"
MY_STOP = "70018" # T stop: Chinatown - Outbound
MY_TIME_TO_T = 240 # time to get to the T stop in seconds (4 minutes)
MY_TIME_TO_WORK = 600 # time to get to work in seconds (10 minutes)

# other variables
TIME_FORMAT = "%H:%M" # "%H:%M:%S"
MBTA_REFRESH_TIME = 60 # in seconds

mbta_parameters = {
			  "api_key": MBTA_TOKEN,
			  "stop": MY_STOP,
			  "format": MBTA_FORMAT,
			  }

def sort_key(d):
    return d['pre_dt']

def get_conditions_weather():
    response = requests.get(WEATHER_CONDITIONS_ENDPOINT)
    print("%s -- %s -- %s" % (datetime.now(), response.url, response))
    return response.json()

def get_hourly_weather():
    response = requests.get(WEATHER_HOURLY_ENDPOINT)
    print("%s -- %s -- %s" % (datetime.now(), response.url, response))
    return response.json()

def get_trains():
    response = requests.get(MBTA_ENDPOINT, params=mbta_parameters)
    print("%s -- %s -- %s" % (datetime.now(), response.url, response))
    trains = response.json()

    # sort trains on departure time
    sorted_trains = sorted(trains["mode"][0]["route"][0]["direction"][0]["trip"], key=sort_key, reverse=False)
    return sorted_trains

def send_message(m):
	print("%s -- message -- %s" % (datetime.now(), m))
	response = requests.post(IFTTT_ENDPOINT, data=m)
	print("%s -- %s -- %s" % (datetime.now(), response.url, response))

def time_string(t):
	ts = time.strftime(TIME_FORMAT, time.localtime(t))
	return ts

def print_trains(et):

	# predicted departure time fist 2 trains (epoch integer)
	predicted_time = int(et[0]["pre_dt"])
	nt_predicted_time = int(et[1]["pre_dt"])

	# current time and delta between current time (epoch integer) and predicted departure time 
	current_time = int(time.time())
	time_delta = predicted_time - current_time

	# leave home (in) time is the difference between current time and predicted time, subtract time to the t
	# e.g. t arrives in 12 minutes, takes 5 minutes to t: need to leave in (12 - 5) = 7 minutes
	leave_home_time = time_delta - MY_TIME_TO_T

	# arrival time at work 
	arrival_time = predicted_time + MY_TIME_TO_WORK
	nt_arrival_time = nt_predicted_time + MY_TIME_TO_WORK

	# predicted departure time string first eligible train
	predicted_time_string = time_string(predicted_time)
	arrival_time_string = time_string(arrival_time)
	nt_arrival_time_string = time_string(nt_arrival_time)

	current = "Train departing at %s." % (predicted_time_string)
	catch = "Get to work at %s." % (arrival_time_string)
	nt = "The next train will get you to work at %s." % (nt_arrival_time_string)

	mbta_limit = 0
	countdown = leave_home_time

	# countdown either 60 seconds or until 0
	while (mbta_limit <= MBTA_REFRESH_TIME) and (countdown > 0):

		if countdown == 120:

			two_minute_message = "%s\nLeave in 2 MINUTES to %s\n%s" % (current, catch.lower(), nt)

			send_message({"value2":two_minute_message})

		if countdown == 15:

			now_message = "Leave NOW!\n%s\n%s\n%s" % (current, catch, nt)

			send_message({"value2":now_message})

		mbta_limit = mbta_limit + 1
		countdown = countdown - 1
		time.sleep(1)

	return

def parse_trains(t):

	# TODO: print alert info

	time_start = time.time()

	time_now = 0 

	while (time_start + APP_RUN_TIME) > time_now:

		# eligible train list variable
		eligible_trains = []

		# go through list
		for train in t:
			
			# predicted departure and current time, delta between the two (epoch integer)
			p_t = int(train["pre_dt"])
			c_t = int(time.time())
			t_d = (p_t - c_t)

			# check to make sure that i can still make the train, if so append
			if (MY_TIME_TO_T < t_d):

				eligible_trains.append(train)

		print_trains(eligible_trains)

		# call mbta API for updated information, sort trains
		t = get_trains()

		time_now = time.time()

def parse_conditions(w):

	greeting = "Good morning %s!" % (MY_NAME)
	conditions_message = str("Weather: %s, feels like %s." % (w["current_observation"]["weather"].lower(), w["current_observation"]["feelslike_c"]))
	image_url = w["current_observation"]["icon_url"]

	send_message({"value1":greeting,"value2":conditions_message,"value3":image_url})

def parse_weather(w):

	rain = 0

	now_day = datetime.now().day

	hourly_message = ""

	for hour in w["hourly_forecast"]:

		hour_int = int(hour["FCTTIME"]["hour"])
		day_int = int(hour["FCTTIME"]["mday"])

		if ((hour_int == 8) or (hour_int == 9) or (hour_int == 17) or (hour_int == 18)) and day_int == now_day:

			if int(hour["qpf"]["metric"]) > 0:
				rain += 1
				hourly_message =  "%s: %s (%scm, %s percent chance), feels like %s.\n" % (hour["FCTTIME"]["civil"], hour["wx"].lower(), hour["qpf"]["metric"], hour["pop"], hour["feelslike"]["metric"])

			else:
				hourly_message = "%s: %s, feels like %s.\n" % (hour["FCTTIME"]["civil"], hour["wx"].lower(), hour["feelslike"]["metric"])

	if rain == 0:
		hourly_message = "You should bike today!"

	else:
		hourly_message += "It's raining. You should take the T today!"

	send_message({"value2":hourly_message})

	return rain

def main():

	weater_conditions = get_conditions_weather()

	parse_conditions(weater_conditions)

	weather_hourly = get_hourly_weather()

	rain = parse_weather(weather_hourly)
	# rain = 2

	if rain > 0:

		print("%s: Waiting for T info for %s seconds..." % (datetime.now(), WAIT_UNTIL_T_TIME))

		time.sleep(WAIT_UNTIL_T_TIME)

		print("%s: Getting T info" % (datetime.now()))

		trains = get_trains()

		parse_trains(trains)

	else:
		print("%s: No rain, exiting app!" % (datetime.now()))

	return

main()