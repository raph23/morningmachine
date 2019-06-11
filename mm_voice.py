import os
import requests
import time
import json
import random
from datetime import datetime

import aiy.audio
import aiy.cloudspeech
import aiy.voicehat

import credentials

# i'm leaving in 10 minutes
# instead of app run time, set var for how many trains you want to hear?
# turn off the lights
# cancel with button, multithreading?

# debug
LINE = "\n ----------------------------- \n"

# my info
MY_NAME = "Raph"
MY_STOP = "70018" # T stop: Chinatown - Outbound
MY_TIME_TO_T = 240 # time to get to the T stop in seconds (4 minutes)
MY_TIME_TO_WORK = 600 # time to get to work in seconds (10 minutes)

# times:
APP_RUN_TIME = 5*60 # run time (5 minutes)
MESSAGE_DELAY = 15 # delay in receiving push notification

# end points
WEATHER_CONDITIONS_ENDPOINT = credentials.WEATHER_CONDITIONS_ENDPOINT
WEATHER_HOURLY_ENDPOINT = credentials.WEATHER_HOURLY_ENDPOINT
IFTTT_ENDPOINT = credentials.IFTTT_ENDPOINT
MBTA_ENDPOINT = "https://api-v3.mbta.com/predictions?filter[stop]=" + MY_STOP # https://api-v3.mbta.com/stops/70018

# mbta variables
MBTA_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S-04:00'
MBTA_REFRESH_TIME = 60 # in seconds
MBTA_PARAMETERS = {
			  "api_key": credentials.MBTA_TOKEN,
			  }

# other variables
TIME_FORMAT = "%I:%M %p" # or "%H:%M:%S"

def dump(r, n):
	time_now = time.time()
	time_now_string = time.strftime('%m-%d-%Y', time.localtime(time_now))
	file_name = ("api_response/%s_%s.json") % (time_now_string, n)

	with open(file_name, 'w') as outfile:
	    json.dump(r, outfile)
	return

def get_api(endpoint, name):
	response = requests.get(endpoint)
	print_response(response)
	dump(response.json(), name)
	return response.json()

def get_trains():
    response = requests.get(MBTA_ENDPOINT, params=MBTA_PARAMETERS)
    print_response(response)
    dump(response.json(), "TRAINS")
    train_data = response.json()

    # print(LINE)
    # pprint(train_data)
    # print(LINE)

    trains = train_data["data"]
    train_departures = []

    for train in trains:
    	# pprint(train["attributes"]["departure_time"])
    	epoch_time = int(time.mktime(time.strptime(train["attributes"]["departure_time"], MBTA_TIME_FORMAT)))
    	train_departures.append(epoch_time)

    sorted_trains = sorted(train_departures)



    # print(LINE)
    # pprint(sorted_trains)
    # print(LINE)
   
    return sorted_trains

def send_message(m):
	print("%s -- <Message> -- %s" % (datetime.now(), m))

	# DEBUG: ENABLE/DISABLE IFFT
	response = requests.post(IFTTT_ENDPOINT, data=m)
	print_response(response)
	return

def time_string(t):
	ts = time.strftime(TIME_FORMAT, time.localtime(t))
	return ts

def print_response(r):
	print("%s -- %s -- %s" % (datetime.now(), r, r.url))
	return

def print_hourly(c):
	for conditions in c:
		print("%s -- <%s> -- %s" % (datetime.now(), conditions["name"], conditions["hour"]))
	return

def day_message():
	# monday = 0, sunday = 6
	day_of_week = datetime.today().weekday()

	if day_of_week == 0:
		monday_message = "Bring your water bottle!"
		send_message({"value2":monday_message})
		aiy.audio.say(monday_message)
	return

def print_trains(et):

	# predicted departure time fist 2 trains (epoch integer)
	predicted_time = et[0]
	nt_predicted_time = et[1]

	# DEBUG
	# print(predicted_time)
	# print(nt_predicted_time)

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

	# DEBUG
	# print(LINE)
	# print(predicted_time_string)

	t_info_message_1 = "Train departing at %s\n" % (predicted_time_string)
	t_info_message_2 = "Catching this train will get you to work at %s\n" % (arrival_time_string)
	t_info_message_3 = "The next train will get you to work at %s" % (nt_arrival_time_string)
	t_info_message = t_info_message_1 + t_info_message_2 + t_info_message_3

	mbta_limit = 0
	countdown = leave_home_time

	# countdown either 60 seconds or until 0
	while (mbta_limit <= MBTA_REFRESH_TIME) and (countdown > 0):

		# print(countdown)

		if countdown == (120 + MESSAGE_DELAY):

			send_message({"value1":"Leave in 2 minutes:", "value2":t_info_message})
			aiy.audio.say("Leave in 2 minutes!")
			aiy.audio.say(t_info_message_1)
			aiy.audio.say(t_info_message_2)
			aiy.audio.say(t_info_message_3)

		if countdown == (0 + MESSAGE_DELAY):

			send_message({"value1":"Leave NOW!", "value2":t_info_message})
			aiy.audio.say("Leave now!")
			aiy.audio.say(t_info_message_1)
			aiy.audio.say(t_info_message_2)
			aiy.audio.say(t_info_message_3)

		mbta_limit = mbta_limit + 1
		countdown = countdown - 1
		time.sleep(1)
	return

def parse_trains(t):

	# TODO: print alert info

	time_start = time.time()
	time_now = 0
	train_messages = 0

	while (time_start + APP_RUN_TIME) > time_now:

		# eligible train list variable
		eligible_trains = []

		# go through list
		for train in t:
			
			# predicted departure and current time, delta between the two (epoch integer)
			p_t = train
			c_t = int(time.time())
			t_d = (p_t - c_t)

			# check to make sure that i can still make the train, if so append
			if (MY_TIME_TO_T < t_d):

				eligible_trains.append(train)

		if train_messages == 0:
			predicted_time = eligible_trains[0]
			predicted_time_string = time_string(predicted_time)
			t_info_message_1 = "First train departing at %s\n" % (predicted_time_string)
			aiy.audio.say(t_info_message_1)

		train_messages += 1
		
		print_trains(eligible_trains)

		# call mbta API for updated information, sort trains
		t = get_trains()

		time_now = time.time()
	return

def parse_conditions(w):

	greeting = "Good morning %s!" % (MY_NAME)
	conditions_message = str("Weather: %s, feels like %s." % (w["current_observation"]["weather"].lower(), w["current_observation"]["feelslike_c"]))
	image_url = w["current_observation"]["icon_url"]

	temp_string = w["current_observation"]["feelslike_c"]
	temp_float = float(temp_string)
	temp_round = round(temp_float, 0)
	temp_int = int(temp_round)

	conditions_message_audio = str("The weather is %s, feels like %s degrees" % (w["current_observation"]["weather"].lower(), temp_int))

	send_message({"value1":greeting,"value2":conditions_message,"value3":image_url})
	aiy.audio.say(conditions_message_audio)
	return

def parse_weather(w):

	rain = 0
	now_day = datetime.now().day
	hourly_message = ""
	hourly_conditions = []
	precipitation_by_hour = {"name": "Precipitation", "hour": {}}
	percent_by_hour = {"name": "Percent", "hour": {}}
	temperature_by_hour = {"name": "Temperature", "hour": {}}

	for hour in w["hourly_forecast"]:

		hour_int = int(hour["FCTTIME"]["hour"])
		day_int = int(hour["FCTTIME"]["mday"])

		if ((hour_int == 8) or (hour_int == 9) or (hour_int == 17) or (hour_int == 18)) and day_int == now_day:

			precipitation_by_hour["hour"][hour_int] = hour["qpf"]["metric"]
			temperature_by_hour["hour"][hour_int] = hour["feelslike"]["metric"]
			percent_by_hour["hour"][hour_int] = hour["pop"]

			if int(hour["qpf"]["metric"]) > 0:
				rain += 1
				hourly_message +=  "%s: %s (%scm, %s percent chance), feels like %s\n" % (hour["FCTTIME"]["civil"], hour["wx"].lower(), hour["qpf"]["metric"], hour["pop"], hour["feelslike"]["metric"])
				# add audio here, might need to do some conversion
			else:
				hourly_message += "%s: %s, feels like %s\n" % (hour["FCTTIME"]["civil"], hour["wx"].lower(), hour["feelslike"]["metric"])
				# add audio here, might need to do some conversion

	if rain == 0:
		hourly_message_title = "It's not raining. You should bike today:"
		aiy.audio.say(hourly_message_title)

	else:
		hourly_message_title = "It's raining. You should take the T today:"
		aiy.audio.say(hourly_message_title)

	send_message({"value1":hourly_message_title, "value2":hourly_message})

	hourly_conditions.append(precipitation_by_hour)
	hourly_conditions.append(percent_by_hour)
	hourly_conditions.append(temperature_by_hour)
	print_hourly(hourly_conditions)

	return rain

def leaving():
	print("%s -- Getting T info" % (datetime.now()))
	trains = get_trains()
	parse_trains(trains)

def weather():
	print("%s -- Getting weather info" % (datetime.now()))
	day_message()
	weater_conditions = get_api(WEATHER_CONDITIONS_ENDPOINT, "WEATHER_CONDITIONS")
	parse_conditions(weater_conditions)
	weather_hourly = get_api(WEATHER_HOURLY_ENDPOINT, "WEATHER_HOURLY")
	rain = parse_weather(weather_hourly)

def elena():
	compliments = [
			  "she is the most amazing girl in the world",
			  "she is pretty cool",
			  "she is a little crazy",
			  "she is the best, smartest chubster"
			  ]

	aiy.audio.say(compliments[random.randint(0, 3)])

def main():
    recognizer = aiy.cloudspeech.get_recognizer()
    recognizer.expect_phrase('i am leaving')
    recognizer.expect_phrase('weather')
    recognizer.expect_phrase('turn off the light')
    recognizer.expect_phrase('turn on the light')
    recognizer.expect_phrase('blink')
    recognizer.expect_phrase('repeat after me')
    recognizer.expect_phrase('elena')

    button = aiy.voicehat.get_button()
    led = aiy.voicehat.get_led()
    aiy.audio.get_recorder().start()

    while True:
        print('Press the button and speak')
        button.wait_for_press()
        print('Listening...')
        text = recognizer.recognize()
        if text is None:
            print('Sorry, I did not hear you.')
        else:
            print('You said "', text, '"')
            if 'leaving' in text:
                leaving()
            elif 'weather' in text:
                weather()
            elif 'Elena' in text:
            	elena() 
            elif 'turn on the light' in text:
                led.set_state(aiy.voicehat.LED.ON)
            elif 'turn off the light' in text:
                led.set_state(aiy.voicehat.LED.OFF)
            elif 'blink' in text:
                led.set_state(aiy.voicehat.LED.BLINK)
            elif 'repeat after me' in text:
                to_repeat = text.replace('repeat after me', '', 1)
                aiy.audio.say(to_repeat)
            elif 'goodbye' in text:
                os._exit(0)

if __name__ == '__main__':
    main()