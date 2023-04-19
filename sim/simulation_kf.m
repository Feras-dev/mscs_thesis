% Tested with MATLAB 2022R 64-bit on Windows 11

% Define the parameters
g = 9.81; % acceleration due to gravity [m/s^2]
l = 1; % length of pendulum [m]
b = 0.1; % friction coefficient [kg/s]

% Define the initial conditions
theta_0 = 90; % true initial angle [deg]
omega_0 = 0; % true initial angular velocity [deg/s]

% Define the time step and total time of the simulation
dt = 0.01; % time step [s]
T = 80; % total time [s]

% Create the time and state arrays
x_time = 0:dt:T; % time array
y_true = zeros(size(x_time)); % true angle array
omega = zeros(size(x_time)); % true angular velocity array
y_measured = zeros(size(x_time)); % measured angle array
y_estimated = zeros(size(x_time)); % estimated angle array
y_error = zeros(size(x_time)); % error between true and estimated array

% Set the initial conditions and convert them from deg to rad
y_true(1) = deg2rad(theta_0);
omega(1) = deg2rad(omega_0);
y_estimated(1) = deg2rad(theta_0);
y_error(1) = 0;

% Define the measurement noise and process noise
measurement_noise = 0.1; % (rad)
process_noise = 0.01; % (rad/s)

% Initialize the Kalman filter
x = [theta_0; omega_0]; % initial state
P = eye(2); % initial covariance
A = [1 dt; -(g/l)*dt 1- (b/l)*dt]; % state transition matrix
B = [dt^2/2; dt]; % control input matrix
H = [1 0]; % measurement matrix
Q = [dt^3/3, dt^2/2; dt^2/2, dt]*process_noise^2; % process noise covariance
R = measurement_noise^2; % continuos measurement noise covariance

% Loop through the time steps and update the state
for i = 1:length(x_time)-1
    % True simulated state update
    omega(i+1) = omega(i) - (g/l)*sin(y_true(i))*dt - (b/l)*omega(i)*dt;
    y_true(i+1) = y_true(i) + omega(i+1)*dt;
    
    % Measurement update
    y_measured(i+1) = y_true(i+1) + measurement_noise*randn;
    
    % Kalman filter prediction step
    x_pred = A*x;
    P_pred = A*P*A' + Q;
    
    % Kalman filter correction step
    K = P_pred*H'*inv(H*P_pred*H' + R);
    x = x_pred + K*(y_measured(i+1) - H*x_pred);
    P = P_pred - K*H*P_pred;
    y_estimated(i+1) = x(1);

    % calculate error between true and estimated angle
    y_error(i+1) = y_true(i+1) - y_estimated(i+1);
end

% convert all angle values from radians back to degrees
y_true = rad2deg(y_true);
omega = rad2deg(omega);
y_measured     = rad2deg(y_measured);
y_estimated = rad2deg(y_estimated);

% Calculate the RMSE between y_true and y_estimated
RMSE = sqrt(mean(y_error.^2));

% Plot the results
visualization(x_time, y_true, y_measured, y_estimated, y_error, RMSE, ...
    theta_0, omega_0, b, 'KF');