#!/usr/bin/env python3
"""
Real-Time Speech Recognition & Speaker Identification System
Setup and run script

This script helps set up and run the speech recognition system.
It can install dependencies, start services, and manage the application.
"""

import os
import sys
import subprocess
import argparse
import logging
import asyncio
import signal
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SpeechRecognitionSystemManager:
    """Manager for the speech recognition system"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        self.processes = []
    
    def check_python_version(self):
        """Check if Python version is compatible"""
        if sys.version_info < (3, 8):
            logger.error("Python 3.8 or higher is required")
            sys.exit(1)
        logger.info(f"Python version: {sys.version}")
    
    def check_dependencies(self):
        """Check if required dependencies are available"""
        try:
            import torch
            import whisper
            import fastapi
            import motor
            logger.info("Core dependencies are available")
            return True
        except ImportError as e:
            logger.warning(f"Missing dependency: {e}")
            return False
    
    def install_dependencies(self):
        """Install Python dependencies"""
        logger.info("Installing Python dependencies...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ], cwd=self.root_dir, check=True)
            logger.info("Python dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Python dependencies: {e}")
            sys.exit(1)
    
    def install_frontend_dependencies(self):
        """Install frontend dependencies"""
        if not (self.frontend_dir / "package.json").exists():
            logger.warning("Frontend package.json not found, skipping frontend setup")
            return
        
        logger.info("Installing frontend dependencies...")
        try:
            # Check if npm is available
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
            
            subprocess.run([
                "npm", "install"
            ], cwd=self.frontend_dir, check=True)
            logger.info("Frontend dependencies installed successfully")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("npm not found or failed to install frontend dependencies")
    
    def setup_environment(self):
        """Set up environment configuration"""
        env_file = self.root_dir / ".env"
        env_example = self.root_dir / ".env.example"
        
        if not env_file.exists() and env_example.exists():
            logger.info("Creating .env file from .env.example")
            env_file.write_text(env_example.read_text())
            logger.info("Please edit .env file with your configuration")
    
    def check_mongodb(self):
        """Check if MongoDB is running"""
        try:
            import pymongo
            client = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            client.admin.command('ismaster')
            logger.info("MongoDB is running")
            return True
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}")
            return False
    
    def start_mongodb(self):
        """Attempt to start MongoDB (platform-specific)"""
        system = os.name
        try:
            if system == "nt":  # Windows
                subprocess.run(["net", "start", "MongoDB"], check=True)
            else:  # Linux/Mac
                subprocess.run(["sudo", "systemctl", "start", "mongod"], check=True)
            logger.info("MongoDB started successfully")
        except subprocess.CalledProcessError:
            logger.warning("Failed to start MongoDB automatically. Please start it manually.")
    
    def build_frontend(self):
        """Build the frontend for production"""
        if not (self.frontend_dir / "package.json").exists():
            logger.warning("Frontend not available, skipping build")
            return
        
        logger.info("Building frontend...")
        try:
            subprocess.run([
                "npm", "run", "build"
            ], cwd=self.frontend_dir, check=True)
            logger.info("Frontend built successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build frontend: {e}")
    
    def run_backend(self):
        """Run the backend server"""
        logger.info("Starting backend server...")
        try:
            # Add backend directory to Python path
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.backend_dir.parent) + os.pathsep + env.get("PYTHONPATH", "")
            
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", "backend.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ], cwd=self.root_dir, env=env)
            
            self.processes.append(process)
            return process
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            return None
    
    def run_frontend_dev(self):
        """Run the frontend development server"""
        if not (self.frontend_dir / "package.json").exists():
            logger.warning("Frontend not available")
            return None
        
        logger.info("Starting frontend development server...")
        try:
            process = subprocess.Popen([
                "npm", "start"
            ], cwd=self.frontend_dir)
            
            self.processes.append(process)
            return process
        except Exception as e:
            logger.error(f"Failed to start frontend: {e}")
            return None
    
    def setup(self):
        """Complete setup process"""
        logger.info("Setting up Speech Recognition System...")
        
        self.check_python_version()
        self.setup_environment()
        
        if not self.check_dependencies():
            self.install_dependencies()
        
        self.install_frontend_dependencies()
        
        if not self.check_mongodb():
            logger.info("Starting MongoDB...")
            self.start_mongodb()
            if not self.check_mongodb():
                logger.error("MongoDB is not running. Please start MongoDB manually.")
                sys.exit(1)
        
        logger.info("Setup completed successfully!")
    
    def run(self, mode="dev"):
        """Run the application"""
        logger.info(f"Starting Speech Recognition System in {mode} mode...")
        
        # Start backend
        backend_process = self.run_backend()
        if not backend_process:
            logger.error("Failed to start backend")
            return
        
        # Start frontend based on mode
        if mode == "dev":
            frontend_process = self.run_frontend_dev()
        else:
            self.build_frontend()
            logger.info("Frontend built. Backend will serve static files.")
        
        try:
            logger.info("System is running. Press Ctrl+C to stop.")
            
            # Wait for processes
            for process in self.processes:
                process.wait()
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.stop()
    
    def stop(self):
        """Stop all running processes"""
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.warning(f"Error stopping process: {e}")
        
        self.processes.clear()
        logger.info("All processes stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Speech Recognition System Manager")
    parser.add_argument("command", choices=["setup", "run", "dev", "build", "stop"],
                      help="Command to execute")
    parser.add_argument("--verbose", "-v", action="store_true",
                      help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    manager = SpeechRecognitionSystemManager()
    
    if args.command == "setup":
        manager.setup()
    elif args.command == "run":
        manager.run(mode="prod")
    elif args.command == "dev":
        manager.run(mode="dev")
    elif args.command == "build":
        manager.build_frontend()
    elif args.command == "stop":
        manager.stop()


if __name__ == "__main__":
    main()
