# script to restart the nvargus-daemon (includes gst-launcher-v1.0)
# in case it didn't have a chance to close gracefully (e.g., program crashed).

echo "This script will stop nvargus-daemon (including gst-launcher-v1.0), and restart it."
read -n1 -s -r -p $"To cancel, press ctrl+c now. Otherewise, enter 'y' to continue:" user_input
if [ "$user_input" = 'y' ]; then
    echo ""
    echo "step [1/2]: stop nvargus-daemon.."
    sudo service nvargus-daemon stop;
    echo "step [1/2]: DONE"
    echo "step [2/2]: start nvargus-daemon.."
    sudo service nvargus-daemon start;
    echo "step [2/2]: DONE"
else
    echo ""
    exit;
fi