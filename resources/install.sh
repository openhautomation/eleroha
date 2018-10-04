touch /tmp/dependancy_eleroha_in_progress
echo 0 > /tmp/dependancy_eleroha_in_progress
echo "Launch install of eleroha dependancy"
sudo apt-get update
echo 50 > /tmp/dependancy_eleroha_in_progress
sudo apt-get install -y python-serial python-requests python-pyudev
echo 100 > /tmp/dependancy_eleroha_in_progress
echo "Everything is successfully installed!"
rm /tmp/dependancy_eleroha_in_progress
