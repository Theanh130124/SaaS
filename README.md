Tạo VPC  10.0.0.0/16  


(Khác 2 zone để chết 1 zone vẫn còn zone khác
2 subnet - public - chạy EC2 django ,  private - chạy RDS django (ban đầu con này tạo public để không dùng SSH key - còn không thì dùng Putty)



Tạo internetgetwate rồi attch vào vpc trên


Tạo routertable(tạo 2 con 1 con intenetgetewate , 1 con local)
định tuyến mạng của subnet
![image](https://github.com/user-attachments/assets/30034157-f683-41cf-b2f1-e35b87c4454a)

![image](https://github.com/user-attachments/assets/d27fd784-bdb9-4862-9a97-11eb699bb58d)

anywhere



Tạo securitygr(Phải có ICMPV4 trong hình chưa có)

![image](https://github.com/user-attachments/assets/2a350185-aa8e-4058-b408-a25504a7cd30)


Tạo 2 ec2 và add nó vào 

Tạo con RDS -> kết nối tới - 1 con EC2

-> 









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


Tạo RDS dùng EC2 để mở dùng private Ip (không mở public khi tạo EC2) -> vì sẽ  nằm trong cùng VPC để giao tiếp nội bộ



đi cài database cho EC2 chứa rds  

xong tạo database(tạo trên ec chứa rds -> rồi liên kết) 
rồi python3 manage.py migrate 




ping private trong database bằng con ec2 trong cùng 1 vpc
