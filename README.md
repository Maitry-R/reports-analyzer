# User Access Analyzer

This Streamlit application analyzes user access rights, comparing assigned group permissions with actual access rights to identify discrepancies. It provides a dashboard with visualizations and export options for further analysis.

## Features

-   **User Access Analysis:** Identifies users with extra access rights beyond their group permissions.
-   **Group-to-Access Mapping:** Displays group-to-access mappings.
-   **Public Access Handling:** Accounts for `*PUBLIC` access as default for all users.
-   **Interactive Visualizations:** Provides interactive charts for access distribution and group membership.
-   **User Search:** Allows searching for specific users.
-   **Data Export:** Exports analysis results in CSV format.
-   **Access Export:** Exports users and their groups and accesses based on selected access rights.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**

    -   **On Windows:**

        ```bash
        venv\Scripts\activate
        ```

    -   **On macOS and Linux:**

        ```bash
        source venv/bin/activate
        ```

4.  **Install the required packages:**

    ```bash
    pip install streamlit pandas plotly
    ```

## Usage

1.  **Run the application:**

    ```bash
    streamlit run app.py
    ```
    or for the access export page:
    ```bash
    streamlit run pages/access_export.py
    ```

2.  **Upload CSV files:**
    -   `user_groups` file: Contains user group assignments (`USER_NAME`, `MAIN_GROUP`, `ADDL_GROUP`).
    -   `master_users_groups` file: Contains user access rights (`JNUSER`, `VHFROM`).

3.  **Analyze the data:**
    -   View the dashboard with summary statistics and visualizations.
    -   Explore group-to-access mappings and user access analysis.
    -   Search for specific users.
    -   Download analysis results in CSV format.
    -   In the access export page you can select access rights to filter by, and then download the results.

## File Format Requirements

-   **user\_groups.csv/txt:**
    -   Columns: `USER_NAME`, `MAIN_GROUP`, `ADDL_GROUP`
    -   `ADDL_GROUP` can contain multiple groups separated by commas or spaces.

-   **master\_users\_groups.csv/txt:**
    -   Columns: `JNUSER`, `VHFROM`
    -   `JNUSER` starting with "GR" denote group names.
    -   `JNUSER` equal to "\*PUBLIC" denote public access rights.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License.

## Developer

Developed by Maitry Rawal