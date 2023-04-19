% Tested with MATLAB 2022R 64-bit on Windows 11

function visualization(x_time, y_true, y_measured, y_estimated, ...
    y_true_estimated_err, RMSE, theta_0, omega_0, b, method)
    % This function visualizes the true, measured, and estimated values of 
    % a system, along with the initial conditions and a method name

    % clear figure
    clf;

    % Set up the figure and axes
    subplot(2,1,1);
    
    hold on;

    % Plot the true, measured, and estimated values
    plot(x_time, y_true, 'Color', "#0072BD", 'LineWidth', 2);
    plot(x_time, y_measured, 'Color', "#77AC30", 'MarkerSize', 4, ...
        'LineStyle', ':');
    plot(x_time, y_estimated, 'Color', "#D95319", 'LineWidth', 1.5, ...
        'LineStyle', '--');
    
    % Add the gray lines at +/-90 and origin
    yline(90, '--', "+90");
    yline(-90, '--', "-90");
    yline(0, ':k');

    % Add the legend and title
    legend('True simulated', 'Measured', 'Estimated', '', '');
    title(strcat("Estimation of Simple Pendulum's Angular Position Using ", ...
        method, ' (\theta_0=', num2str(theta_0), ", \omega_0=", ...
        num2str(omega_0), ", b_0=", num2str(b), ")"));

    % Set the axis labels and limits
    xlabel('Time [s]');
    ylabel('Angular Position [deg]');
    xlim([x_time(1), x_time(end)]);

    hold off;
    hold on;

    % plot error between true simulated and estimated y-values
    subplot(2,1,2);
    plot(x_time, y_true_estimated_err);
     % Add the gray lines at +/-90
    yline(0, ':k');
    title(strcat('Error Between True Simulated and ', ...
        'Estimated Angular Position Using ', method, " (RMSE=", num2str(RMSE), " deg)"));
    xlabel('Time [s]');
    ylabel('Error in Angular Position Estimation [deg]');
    xlim([x_time(1), x_time(end)]);

    hold off;
end