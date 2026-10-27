# IDOM-SMART
IDOM Selection Methodology for Assesment of Reactor Technologies (IDOM-SMART) is an innovative decision-support tool designed to assist in the selection of advanced reactor technologies for various applications. Leveraging the Analytical Hierarchy Process (AHP) methodology, IDOM-SMART provides a structured and systematic approach to evaluate and prioritize different reactor technologies based on multiple criteria.
IDOM-SMART is directly connected to the IDOM-ARIS database containing information of over 80 nuclear reactor designs.
## Requirements

- The only requirements to be able to install IDOM-SMART is a working python 3 installation (with python in the PATH environment variable), internet connection and ~1Gb of free space in disk.
- (Optional) [Graphviz](https://www.graphviz.org/): If installed, it will be used to create the image of the hierarchy in the report. If not, a simple text hierarchy will be used.
## Installation
To install IDOM-SMART, 
1. Download your desired version:
	- For the stable version (recomended): Download the latest version from the [Releases Section](https://gitea.nuclear.idom.com/cristian.garrido/idom-smart/releases)
	- For the development version: Download this repository by clicking the *Download ZIP* button.
2. Extract the downloaded zip file in your desired installation folder (it is prefered to use simple paths such as C:\).
3. Double click on the **install-win.bat** script to install.
Note: the script **install-win.bat** will create a python virtual environment inside the installation folder and install all necessary modules.
## Post-installation configuration
### Configuring access to IDOM-ARIS
IDOM-SMART allows the selection of alternatives directly from the IDOM-ARIS database (ensure you have access to the database first, otherwise contact the owner, cristian.garrido@idom.com). In order to be able to connect to the Sharepoint site, a file named *.venv* needs to be created in the installation folder. In this file you need to add two lines defining your username (*CLIENT_ID*) and your password (*CLIENT_SECRET*). An example of the contents of the .env file is provided below:
```
CLIENT_ID="my.user.name@idom.com"
CLIENT_SECRET="my.idom.password"
```
**Important: If you ever share the IDOM-SMART folder, make sure you are not sharing the .env file!!**
### Adding a Desktop shortcut
For convinience, it is recommended to add a Desktop shortcut to the **run-idom-smart.bat** script that is used to launch the application.
## Troubleshooting & Reporting Bugs
If you run into problems installing IDOM-SMART or find any bugs, please contact cristian.garrido@idom.com

## TODO:
### Main developments
1. Implement sensitivity analysis
2. Option to generate Google forms with questionaires (https://developers.google.com/forms/api/quickstart/python?hl=es-419)
### Possible improvements
3. Propose change to the values in the Saaty scale when the consistency ratio is out of range
4. Link with the rest of IDOM-ARIS columns
5. ~~In the Criteria Edition tab, add a section to include description for goal, criteria and subcriteria.~~
6. Add Option to freeze individual comparisons so that they cannot be modified. And if the criteria or subcriteria of this comparisons are modified, the comparison stays the same (i.e. Allow to edit a criteria without having to perform all comparisons again)
7. ~~Try to improve the criteria edition interface: Allow modifying the name of the selected criteria (without having to enter the text box), allow movement with Up/Down arros in keyboard, etc.~~
8. ~~Move Generate Report button to webview menu.~~
9. Add logging support.
10. Add tqdm progress bar at the bottom.
