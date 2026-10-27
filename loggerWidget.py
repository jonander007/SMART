import logging
import ipywidgets as widgets
from IPython.display import display, Javascript, clear_output, HTML

class LoggerWidget:
    LOG_COLORS = {
        'DEBUG': 'blue',
        'INFO': 'green',
        'WARNING': 'orange',
        'ERROR': 'red',
        'CRITICAL': 'purple'
    }
    
    html_content = """
    <div style="
        overflow: auto;
        max-height: 80px;
        display: flex;
        flex-direction: column-reverse;
        border: 1px solid #ccc;
        padding: 10px;
        font-family: monospace;
    ">
        <div class="log-content">
        </div>
    </div>
    """

    def __init__(self, file_only=False, log_file='log.log'):
        """
        Initialize the LoggerWidget class.

        Args:
            file_only (bool): If True, disables widgets and only logs to a file.
            log_file (str): Path to the log file.
        """
        self.file_only = file_only
        self.log_file = log_file

        # Set up logging
        self.logger = logging.getLogger('notebook_logger')
        self.logger.setLevel(logging.INFO)

        # File logging setup
        self.file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter('[ %(levelname)s ] %(asctime)s -%(name)s- : %(message)s')
        self.file_handler.setFormatter(file_formatter)
        self.logger.addHandler(self.file_handler)
        self.all_widgets = None

        # Skip widget setup if file_only is True
        if not file_only:
            self._setup_widgets()

    def _setup_widgets(self):
        """Setup widgets for logging controls and output."""
        self.log_output = widgets.HTML(
            value=self.html_content,
            layout=widgets.Layout(width='95%', height='120px')
        )

        self.clear_button = widgets.Button(
            description='Clear Logs',
            button_style='warning'
        )

        self.log_level_dropdown = widgets.Dropdown(
            options=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            value='INFO',
            description='Log Level:',
            layout=widgets.Layout(width='200px')
        )
        self.output = widgets.Output()

        self.log_controls = widgets.HBox(
            [self.log_level_dropdown, self.clear_button]
        )

        # Display widgets
        self.all_widgets = widgets.VBox([
            self.log_output, 
            self.log_controls,
            self.output
        ])

        # Add widget-based logging handler
        self.widget_handler = self.WidgetLoggerHandler(self.log_output, self.output)
        widget_formatter = logging.Formatter('[ %(levelname)s ] %(asctime)s -%(name)s- : %(message)s')
        self.widget_handler.setFormatter(widget_formatter)
        self.logger.addHandler(self.widget_handler)

        # Connect widget interactions
        self.log_level_dropdown.observe(self._update_log_level, names='value')
        self.clear_button.on_click(self._clear_logs)

    class WidgetLoggerHandler(logging.Handler):
        """Custom logging handler to write logs to an ipywidgets.HTML widget."""
        def __init__(self, widget, output):
            super().__init__()
            self.widget = widget
            self.output = output

        def emit(self, record):
            log_entry = self.format(record)
            # Add color to entry depending on level
            color = LoggerWidget.LOG_COLORS.get(record.levelname, 'black')
            colored_entry = f'<span style="color: {color};">{log_entry}</span>'
            
            # Add log entry as a new line in the HTML content
            current_logs = self.widget.value
            # Find the closing div of log-content
            content_div_end = current_logs.find('</div>', current_logs.find('class="log-content"'))
            
            # Insert the new log entry at the beginning of the content
            updated_logs = (
                current_logs[:content_div_end] +
                colored_entry + '<br/>' +
                current_logs[content_div_end:]
            )
            
            self.widget.value = updated_logs

    def _update_log_level(self, change):
        """Update the log level dynamically."""
        self.logger.setLevel(change['new'])

    def _clear_logs(self, _):
        """Clear logs from the HTML widget."""
        self.log_output.value = self.html_content

    def log(self, level, message):
        """Log a message at the specified level."""
        getattr(self.logger, level.lower())(message)
