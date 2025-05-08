
<h1>Xem hướng dẫn chi tiết tại</h1>


https://www.youtube.com/watch?v=ft4A5dn2v5o

Tạo VPC  10.0.0.0/16  

![{17116F3D-ABBA-498D-9592-DDBC59E2910A}](https://github.com/user-attachments/assets/7f5b276a-3124-4aa2-9f80-1cddb28ab521)

Edit VPC settings -> Enable DNS hostnames lên


![{0F5DA867-B2AE-4FAF-9B65-09E4D2735D47}](https://github.com/user-attachments/assets/883cd6d6-4709-4c45-abc5-de0e9f29d1d5)

Tao 2 subnet (1 subnet public 10.0.1.0/24   1 subnet private 10.0.2.0/24) (Khác 2 zone để chết 1 zone vẫn còn zone khác



![{AF98562E-A134-4EA7-BF4F-633BC60B7BBC}](https://github.com/user-attachments/assets/413a40c8-e8f2-4b45-9803-8046817b8eb7)

![{C969B59C-F959-4332-A498-E48C9D3FDA39}](https://github.com/user-attachments/assets/17420d27-6334-4d9d-abb3-049fadcc4d18)


Tạo 1  internet gateways và nhớ Attach vào VPC

![{CB3893E7-1EEE-4691-8EEC-8B1E89D8CA76}](https://github.com/user-attachments/assets/4993048c-a15b-4ec7-b04c-85f9c9201ab7)




Tao 2 cái router table cho public và private


![{3964EC37-49A3-489F-BBFA-8FAC2CCC180B}](https://github.com/user-attachments/assets/5b8ca8ea-4f92-4eb5-9da4-5127ec925192)
![{692A5C88-9E84-49C8-895F-ADEDFA9BD008}](https://github.com/user-attachments/assets/9a6eabe8-5b67-4a2a-ac75-de1359579395)
 
ở router public chọn Edit router và thêm internet gateways vào

![{7E8D951B-1FBF-4E81-BDE6-DB7B46068676}](https://github.com/user-attachments/assets/a25af19e-817e-4166-a2e2-04cd36e0efc2)

Tạo security -grp như sau 


![{3D1BDA00-04A6-4D84-99BF-36C28D26C04A}](https://github.com/user-attachments/assets/ae952a54-377e-41a6-996e-2454ca7b99e5)

Đi tạo EC2 cho server 

![{12B62203-633A-4C68-B64A-FFBAC9FEF3B6}](https://github.com/user-attachments/assets/4096936b-230a-4bdc-819c-6387f801cdd8)

![{53D60BFB-9170-4B48-BD2A-C1C5E841A24F}](https://github.com/user-attachments/assets/4bab68dc-9c83-423c-adff-5e7bfa515ae4)



Đi tạo RDS

![{84BF7FD5-B174-4FF6-8770-B6BC69AC7AE0}](https://github.com/user-attachments/assets/0ad0b8d3-8bf6-468a-a24d-d6baf8a8649f)
![{089DCBF6-E124-4E15-91A8-CE3FD8874A28}](https://github.com/user-attachments/assets/81890375-512c-40c1-8344-45c7b84c3bab)
![{BF66ABBB-439D-40D3-976E-2CDC066E06DA}](https://github.com/user-attachments/assets/fe5c7155-4e42-4003-8c76-e4ed7f0078be)
![{99A60A58-71F0-48B0-8B78-8792D14D5A2F}](https://github.com/user-attachments/assets/32e860a1-cbb1-4479-8153-ef503fd3f631)
![{EBB07D2E-4357-4053-90D8-4091C1492A4E}](https://github.com/user-attachments/assets/e8e978f9-e303-4783-acfd-bd19b7bfd9f2)
![{7010C740-FBA5-455B-842E-F95A79AF638F}](https://github.com/user-attachments/assets/9d2e49b7-3a80-4daa-884e-4fba66cd0b83)


Rồi tạo ec2 để có thể kết nối với RDS



































ssh: 771236651378781348914







Type
Protocol
Port Range
Source
Giải thích
SSH
TCP
22
Your IP (vd: 113.23.x.x/32)
Chỉ bạn mới SSH vào EC2 được
HTTP
TCP
80
0.0.0.0/0
Mọi người đều có thể truy cập trang web
HTTPS
TCP
443
0.0.0.0/0
Hỗ trợ SSL (nếu có), truy cập bảo mật




cấu hình EC2




Connect EC2 

https://github.com/Theanh130124/SaaS.git


git clone https://github.com/Theanh130124/SaaS.git

ls -lrt

sudo apt update

sudo apt install python3-pip -y


Tạo RDS dùng EC2 để mở dùng private Ip (không mở public khi tạo EC2) -> vì sẽ  nằm trong cùng VPC để giao tiếp nội bộ



đi cài database cho EC2 chứa rds  

xong tạo database(tạo trên ec chứa rds -> rồi liên kết) 
rồi python3 manage.py migrate 




ping private trong database bằng con ec2 trong cùng 1 vpc

--------------


pip install gunicorn


sudo lsof -i :9000

sudo lsof -i :8000



gunicorn --workers 3 --bind 0.0.0.0:9000 SocialApp.wsgi:application



Sử dụng screen:
Cài đặt screen (nếu chưa có):

bash
Copy
Edit
sudo apt-get install screen
Tạo một session mới với screen:

bash
Copy
Edit
screen -S gunicorn-session
Chạy Gunicorn trong session screen:

bash
Copy
Edit
gunicorn --workers 3 --bind 0.0.0.0:8000 SocialApp.wsgi:application
Thoát khỏi session screen nhưng giữ Gunicorn chạy:
Nhấn Ctrl + A, sau đó nhấn D để thoát khỏi session screen.

Để quay lại session screen:

bash
Copy
Edit
screen -r gunicorn-session

sudo kill 4080 4616

------------
sudo chown -R ubuntu:ubuntu /home/ubuntu/SaaS/SocialApp/static
sudo chmod -R 755 /home/ubuntu/SaaS/SocialApp/static



python manage.py collectstatic

