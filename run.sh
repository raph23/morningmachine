cd /home/pi/Desktop/Projects/mm/

rm run_output.txt

date >>run_output.txt

python mm.py >>run_output.txt

date >>run_output.txt

echo END OF RUN >>run_output.txt
