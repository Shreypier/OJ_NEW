# Deploying CodeLANG on AWS (low-cost guide)

This puts the project on one small AWS server (EC2) so it has a public link. It uses
Gunicorn + Nginx, free HTTPS, and Docker for the per-submission sandbox.

Expect about 1 to 2 hours the first time. AWS menus change now and then, so button labels may
differ slightly from what is written here.

```
Browser -> Nginx (HTTPS) -> Gunicorn -> Django
                                         \-> Docker: one throwaway container per submission
```

## 0. Before you start

- A **GitHub account** and this project pushed to a GitHub repository (see step 1).
- An **AWS account** (needs an email, phone number and a card for verification).
- A **free subdomain** from [duckdns.org](https://www.duckdns.org) (step 5). You do not need to buy a domain.

## 1. Put the code on GitHub

This project's repository is https://github.com/Shreypier/OJ_NEW (it is the `origin` of this folder).
It is **public**, and its old commits already contain `db.sqlite3`. That data was published long ago,
so treat any password that was ever stored in it as exposed and change it anywhere else you used it.
From now on `db.sqlite3` is no longer tracked, so new commits do not add to the problem.

GitHub also has a few commits you do not have locally (automatic Docker workflows), so bring them
in first, then push normally (no force-push):

```bash
git fetch origin
git merge origin/master
git push origin master
```

(If you make the repository private, the server will need a GitHub token to clone it. A public
repository is simpler and is what you want to show on a resume anyway.)

## 2. Create the AWS account safely

1. Sign up at aws.amazon.com and finish verification.
2. Turn on **MFA** for the root user (top-right menu, Security credentials).
3. Create a **budget alert** so you are warned about costs:
   Billing and Cost Management, then Budgets, then Create budget, then "Zero spend budget" or a
   monthly cost budget of about **$5**. Add your email.
4. Choose a **region** near you from the top-right menu (for example Mumbai `ap-south-1`).
   Use the same region for everything below.

## 3. Launch the server (EC2)

EC2, then **Launch instance**:

| Setting | Value |
|---|---|
| Name | `codelang` |
| Image (AMI) | **Ubuntu Server 24.04 LTS**, 64-bit (x86) |
| Instance type | **t3.micro** (1 GB RAM, cheapest). Pick **t3.small** (2 GB) if C++ submissions run out of memory. |
| Key pair | **Create new key pair**, type RSA, format `.pem`. It downloads once: keep it safe. |
| Network settings | Allow **SSH** from *My IP*, and allow **HTTP** and **HTTPS** from the internet |
| Storage | **20 GiB** gp3 (the default 8 GiB is too small for Docker images and swap) |

Click **Launch instance**.

## 4. Give it a fixed address (Elastic IP)

EC2, then **Elastic IPs**, then **Allocate Elastic IP address**, then **Associate** it with the
`codelang` instance. This is the public IP that will not change when the server restarts.

> AWS charges a small hourly fee for public IPv4 addresses (about $3.6 a month). Release the
> Elastic IP when you delete the project.

## 5. Get a free web address (DuckDNS)

1. Sign in at duckdns.org (with GitHub or Google).
2. Create a subdomain, for example `mycodelang`, giving `mycodelang.duckdns.org`.
3. Set its **current ip** to your Elastic IP and click **update ip**.

## 6. Connect to the server

Easiest: in the EC2 console select the instance, click **Connect**, choose **EC2 Instance Connect**,
then **Connect**. You get a terminal in your browser.

Or from Windows PowerShell with your key file:

```powershell
icacls .\codelang-key.pem /inheritance:r
icacls .\codelang-key.pem /grant:r "$($env:USERNAME):(R)"
ssh -i .\codelang-key.pem ubuntu@<your-elastic-ip>
```

## 7. Install and start the app

On the server:

```bash
git clone https://github.com/<your-username>/<repo-name>.git ~/codelang
cd ~/codelang
sudo bash deploy/setup_server.sh mycodelang.duckdns.org
```

The script adds swap space, installs Docker, Nginx and Python, builds the sandbox image, creates
the database, and starts the app. It takes several minutes. At the end it prints the next steps.

Now open `http://mycodelang.duckdns.org` in your browser. You should see the landing page.

Then log out and back in once (`exit`, reconnect) so your user can run `docker` without `sudo`.

## 8. Turn on HTTPS

```bash
sudo certbot --nginx -d mycodelang.duckdns.org
```

Answer the questions (give an email, accept the terms, choose to redirect HTTP to HTTPS). Then tell
Django the site is on HTTPS:

```bash
sudo sed -i 's/^DJANGO_HTTPS=0/DJANGO_HTTPS=1/' /etc/codelang.env
sudo systemctl restart codelang
```

## 9. Create your accounts

```bash
cd ~/codelang
./deploy/manage.sh createsuperuser
```

Then sign in at `https://mycodelang.duckdns.org/admin/`. Under **Users**, add employees with
**Staff status** ticked (leave Superuser unticked). Employees sign in at `/accounts/employee_login/`
and add problems and test cases from the Manage page.

## 10. Check that everything works

- [ ] The landing page loads over `https://` with the padlock.
- [ ] You can sign up and log in as a normal user.
- [ ] As an employee, you can create a problem with at least one test case.
- [ ] Submitting a correct solution returns **Accepted**.
- [ ] A submission with `while True: pass` returns **Time Limit Exceeded** after about 10 seconds.

## Updating the site later

Push your changes to GitHub, then on the server:

```bash
cd ~/codelang
./deploy/update.sh
```

## If something goes wrong

| Problem | Look here |
|---|---|
| Site will not load | `sudo systemctl status codelang` and `sudo journalctl -u codelang -n 50` |
| 502 Bad Gateway | The Gunicorn service is down: `sudo systemctl restart codelang` |
| Every submission says "System Error" | `docker ps` (is Docker running?), `docker images` (is `codelang-sandbox` there?), then `./deploy/update.sh` |
| "Sandbox ran out of memory" | `free -h`; use a **t3.small**, or lower `JUDGE_MAX_CONCURRENT` in `/etc/codelang.env` |
| Login or forms fail with a CSRF error | `DJANGO_CSRF_TRUSTED_ORIGINS` in `/etc/codelang.env` must be `https://<your-domain>` |
| HTTPS certificate fails | The DuckDNS name must point at the Elastic IP, and ports 80 and 443 must be open in the security group |

After editing `/etc/codelang.env`, always run `sudo systemctl restart codelang`.

## Costs and shutting down

An idle server still costs money, because AWS bills for running hours, not for visitors.
Roughly: t3.micro about $7.5 a month, plus about $3.6 for the public IPv4 address, plus about $2 for the disk.
Check current prices on the AWS pricing pages.

To **stop all charges** when you no longer need the link:

1. EC2, select the instance, **Instance state**, then **Terminate instance** (the disk is deleted with it).
2. EC2, **Elastic IPs**, select the address, **Release Elastic IP addresses**.
3. Check **Billing** a day later and confirm there are no new charges.

"Stop" is not enough: a stopped instance still pays for its disk and address.

## Security notes

- The app user is in the `docker` group, which is effectively root on that server. That is why this
  server should hold nothing else of value, and why the sandbox flags (no network, memory, CPU and
  process limits, read-only filesystem, non-root user) matter.
- Containers share the host kernel. This is the standard trade-off for an online judge of this size.
- Keep the server updated: `sudo apt update && sudo apt upgrade`.
- Never commit `/etc/codelang.env` or your `.pem` key file.
