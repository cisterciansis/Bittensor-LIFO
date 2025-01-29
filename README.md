# Bittensor-LIFO

## LIFO Accounting for Bittensor TAO

Bittensor-LIFO is a tool designed to implement Last-In-First-Out (LIFO) accounting for Bittensor TAO transactions. It helps you manage and track TAO funds across different wallets, ensuring accurate financial reporting and analysis within the Bittensor network.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Setting Up `read_all_new.py`](#setting-up-read_all_newpy)
- [Usage](#usage)
- [Wallet Types](#wallet-types)

## Features

- **TAO Transaction Tracking:** Monitor incoming and outgoing TAO transactions across multiple wallets.
- **Wallet Categorization:** Differentiate between active wallets and secondary wallets for better fund management.
- **LIFO Accounting:** Apply LIFO principles to manage and report TAO holdings.
- **TAOSTATS API Integration:** Utilize the TAOSTATS API for real-time transaction data.

## Prerequisites

- **Python 3.7 or higher**
- **TAOSTATS API Key:** Obtain an API key from [TAOSTATS](https://dash.taostats.io/login).
- 
## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/cisterciansis/Bittensor-LIFO.git
   cd Bittensor-LIFO
   ```

2. **Create a Virtual Environment (Optional but Recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

## Configuration

### Setting Up `read_all_new.py`

1. **Open `read_all_new.py`**

   Use your preferred text editor to open the `read_all_new.py` file.

2. **Add TAOSTATS API Key**

   Locate the section where the API key should be inserted and add your TAOSTATS API key:

   ```python
   API_KEY = 'your_taostats_api_key_here'
   ```

3. **Add Wallet Addresses**

   Define your wallets by categorizing them into active and secondary wallets.

   - **Active Wallets:** Wallets that receive ongoing large amounts of TAO from the network (e.g., miners, SN owner wallets, validating wallets).

   - **Secondary Wallets:** Wallets holding funds and staking but not actively participating to gain significant TAO.

   ```python
   ACTIVE_WALLETS = [
       'wallet_address_1',
       'wallet_address_2',
       # Add more active wallet addresses here
   ]

   SECONDARY_WALLETS = [
       'secondary_wallet_address_1',
       'secondary_wallet_address_2',
       # Add more secondary wallet addresses here
   ]
   ```

4. **Save the Configuration**

   Ensure all your wallet addresses and the API key are correctly added and save the `read_all_new.py` file.

## Usage

1. **Run `read_all_new.py`**

   This script fetches and processes TAO transactions based on your configuration.

   ```bash
   python3 read_all_new.py
   ```

2. **Run `read_lifo.py`**

   After processing the data, execute the LIFO accounting script to analyze your TAO holdings.

   ```bash
   python3 read_lifo.py
   ```

## Wallet Types

- **Active Wallets:**
  - **Purpose:** Receive large, ongoing amounts of TAO from the network.
  - **Examples:** Miners, SN owner wallets, validating wallets.
  - **Usage:** Actively participate in the network to earn TAO.

- **Secondary Wallets:**
  - **Purpose:** Hold funds and participate in staking without significant TAO earnings.
  - **Usage:** Store and manage TAO without active participation in mining or validating.
