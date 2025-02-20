Installation  
- Install python 3  
update-alternatives --install /usr/bin/python python /usr/bin/python3 1  

- Install pip 3  
sudo apt install python3-pip -y  
update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1  

- Install django  
apt-get install python3-django  

- If django version lower than 3.2 upgrade by command:  
pip install --upgrade django  

- Install some depend packages:  
apt-get install python3-mysqldb  
apt-get install python3-pymysql  
apt-get install libmysqlclient-dev  
pip install mysqlclient  
pip install requests  


- Start Server:  
python3 manage.py runserver 0.0.0.0:8001 &  

Note:  
- Log's Folder: BASE_DIR/logs  
- System get data from database foreach 15 days and save in folder: BASE_DIR/tmp. This folder will be deleted after Optimization finished  
