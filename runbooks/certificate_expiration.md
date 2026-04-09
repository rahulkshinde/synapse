# Runbook: TLS Certificate Expiration

## Severity: CRITICAL
## Category: Security
## Services: Any service using TLS/mTLS

## Symptoms
- Connection refused or TLS handshake failures
- Browser showing "certificate expired" warnings
- Application logs showing SSL/TLS errors
- Monitoring alerts on certificate expiry metrics
- ArgoCD sync failures if Git repo certs expired

## Diagnosis Steps

1. **Check certificate expiry from outside:**
   ```bash
   echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null \
     | openssl x509 -noout -dates
   ```

2. **Check Kubernetes TLS secrets:**
   ```bash
   kubectl get secret <tls-secret> -n <namespace> -o jsonpath='{.data.tls\.crt}' \
     | base64 -d | openssl x509 -noout -dates -subject
   ```

3. **Check cert-manager certificate status:**
   ```bash
   kubectl get certificates -A
   kubectl describe certificate <cert-name> -n <namespace>
   # Look for: Ready=True/False, Renewal Time, Not After
   ```

4. **Check Prometheus for expiry metrics:**
   ```promql
   # Certificates expiring within 7 days
   (x509_cert_not_after - time()) / 86400 < 7
   ```

## Resolution

### Immediate
- If cert-manager managed: trigger renewal
  ```bash
  kubectl delete secret <tls-secret> -n <namespace>
  # cert-manager will automatically issue a new certificate
  ```
- If manually managed: replace the secret with a new certificate
  ```bash
  kubectl create secret tls <name> --cert=new.crt --key=new.key -n <namespace> --dry-run=client -o yaml | kubectl apply -f -
  ```
- Restart affected pods to pick up new cert:
  ```bash
  kubectl rollout restart deployment/<name> -n <namespace>
  ```

### Root Cause Investigation
- cert-manager issuer misconfigured (check ClusterIssuer/Issuer status)
- DNS challenge failing for Let's Encrypt (check DNS propagation)
- ACME rate limits hit (check cert-manager logs)
- Manual certificate not added to rotation schedule

### Prevention
- Use cert-manager with automatic renewal (renewBefore: 30d)
- Alert on certificates expiring within 14 days
- Maintain a certificate inventory with expiration tracking
- Never use self-signed certificates in production without rotation
