```
#install openssl
sudo apt install openssl
#verify openssl is correctly installed
 openssl version -a 
 ```

 Generate the CSR (Certificate SIgning Request)
 ```
openssl req -new -newkey rsa:2048 -nodes -keyout yourdomain.key -out yourdomain.csr
```

You can verify then request
```
openssl req -text -in yourdomain.csr -noout -verify
```
Enter Required Information

You will be prompted to enter information such as:

  * Country Name: Two-letter abbreviation for your country.
  * State or Province Name: Full name of your state.
  * Locality Name: Name of your city.
  * Organization Name: Name of your organization.
  * Organizational Unit Name: Section or sector of your organization.
  * Common Name: The domain name for which you are purchasing the SSL certificate.
  * Emaiul Address: 

[optional] (for testing) self sing the request
```
openssl x509 -in yourdomain.csr -out yourdomain.crt -req -signkey yourdomain.key -days 365
```
