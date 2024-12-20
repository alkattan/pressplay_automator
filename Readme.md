# Automated AB Experiment Management System for Google Play Store

## Overview

This project introduces an automated system for creating, monitoring, and managing AB experiments in the Google Play Store using Google Sheets as a database. The system streamlines the process of AB testing for mobile apps, making it more efficient and user-friendly. With various dedicated sheets for different aspects of AB testing, this system offers a comprehensive solution for app publishers and developers.

## Features

- **Automated Creation and Monitoring of AB Experiments**: Simplifies the process of setting up and tracking AB experiments in the Google Play Store.
- **Google Sheets as Database**: Utilizes a familiar and accessible platform for managing experiment data.
- **Diverse Data Sheets**: Multiple sheets for different purposes, including experiment settings, historical data, and variant tracking.

## Google Sheets Structure

1. **Publisher/App Settings**: Stores configurations for different apps, including basic settings and app-specific details.

2. **Reporting Experiments**: Maintains a historical record of all experiments conducted, allowing for easy reference and analysis.

3. **Reporting Variants**: Tracks the variants of each experiment, updated daily to reflect ongoing changes and results.

4. **Create New Experiment**: Facilitates the insertion of new experiments into the system, ensuring a streamlined process.

5. **Automated_Testing_Experiments**: Holds details of current experiments, including audience targeting, CSL, locale, experiment type, and title.

6. **Automated_Testing_Variants**: Manages the variants for each experiment, with each variant represented as a new row for clarity.

7. **CSLs**: Lists all possible CSLs and locale combinations for use in the Publisher/App Settings sheet, offering a comprehensive reference.

## How it Works

1. **Setting Up**: Enter app configurations in the "Publisher/App Settings" sheet.

2. **Creating Experiments**: Use the "Create New Experiment" sheet to input new experiment details. These are automatically added to the "Automated_Testing_Experiments" sheet.

3. **Monitoring Progress**: Variants and ongoing experiment results are updated daily in the "Reporting Variants" and "Reporting Experiments" sheets.

4. **Analyzing Results**: Historical data is available for analysis to inform future experiments and app improvements.

5. **Stopping Experiments**: When an experiment concludes or requires termination, the system allows for easy stopping and logging of results.

## Requirements

- Access to Google Sheets.
- Basic understanding of AB testing principles.
- Knowledge of Google Play Store app management.

## Setup and Installation

1. Clone the repository or download the project files.
2. Set up Google Sheets according to the provided template.
3. Configure the scripts to connect with your Google Play Store account using the service account.
4. Install the requirements
5. Install Playwright on your system


## Usage
1. Fetch the current App CSLs from the Google Play Console 

2. Generate some icons experiments in the google sheets file https://docs.google.com/spreadsheets/d/16img22ajmEOcVyWrS3sdXSneN0imFqT0VDYpYpCfLe8/edit#gid=690956743

2. Run the main.py file to start the process based on the google sheets data
    python main.py

## Support

For support, please refer to the `support` section in the documentation or raise an issue in the project repository.


*Note: This README is a general overview. Please refer to the detailed documentation for specific instructions and guidelines.*