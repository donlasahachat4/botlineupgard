CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  phone VARCHAR(50) UNIQUE,
  line_user_id VARCHAR(64) UNIQUE,
  is_linked BOOLEAN DEFAULT FALSE,
  verify_token VARCHAR(64),
  registered_ip VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  owner_id VARCHAR(64) NOT NULL,
  balance DECIMAL(10,2) DEFAULT 0,
  locked BOOLEAN DEFAULT FALSE,
  channel ENUM('web','line','shared') NOT NULL,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rounds (
  id INT AUTO_INCREMENT PRIMARY KEY,
  red_odds DECIMAL(5,2) DEFAULT NULL,
  blue_odds DECIMAL(5,2) DEFAULT NULL,
  result ENUM('red','blue') DEFAULT NULL,
  status ENUM('open','closed','settled') NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  round_id INT NOT NULL,
  side ENUM('red','blue') NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  status ENUM('pending','win','lose','cancel') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (round_id) REFERENCES rounds(id)
);

CREATE TABLE IF NOT EXISTS deposits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  slip_path VARCHAR(255),
  status ENUM('pending','approved','rejected') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS registered_bank_accounts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  account_name VARCHAR(100) NOT NULL,
  account_number VARCHAR(50) NOT NULL,
  bank_name VARCHAR(100) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS withdrawal_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  account_name VARCHAR(100) NOT NULL,
  account_number VARCHAR(50) NOT NULL,
  bank_name VARCHAR(100) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(20) DEFAULT 'pending',
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS withdrawals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  bank_name VARCHAR(64),
  bank_account VARCHAR(64),
  status ENUM('pending','approved','rejected') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS streams (
  id INT AUTO_INCREMENT PRIMARY KEY,
  hls_url VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bet_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(64),
  round_id INT,
  side ENUM('red','blue') DEFAULT NULL,
  amount DECIMAL(10,2) DEFAULT 0,
  platform ENUM('web','line') NOT NULL,
  status ENUM('success','failed','rejected') NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  action ENUM('deposit','withdraw') NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  status ENUM('pending','success','failed','rejected') NOT NULL,
  platform ENUM('web','line','admin') NOT NULL,
  slip_url VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  admin_id VARCHAR(64),
  action_type VARCHAR(64) NOT NULL,
  detail TEXT,
  ip_address VARCHAR(64),
  user_agent VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS security_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(64),
  event_type VARCHAR(64) NOT NULL,
  severity VARCHAR(10) NOT NULL,
  detail TEXT,
  ip_address VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS otp_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  code VARCHAR(6) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  valid_until TIMESTAMP NOT NULL,
  is_verified BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS deposit_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  decimal DECIMAL(4,2) NOT NULL,
  full_amount DECIMAL(10,2) NOT NULL,
  ref VARCHAR(64) UNIQUE,
  status ENUM('pending','matched','expired','cancelled') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
