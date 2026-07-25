import re
from locust import HttpUser, task, between
from bs4 import BeautifulSoup

class TechEShopUser(HttpUser):
    # Simulate realistic human delay between 1 to 5 seconds
    wait_time = between(1, 5)

    def on_start(self):
        """
        Executed when a simulated user starts.
        We establish a session and fetch the initial CSRF token.
        """
        self.product_urls = []
        # Hit the home page to get a CSRF cookie
        response = self.client.get("/en/")
        self.csrf_token = self.client.cookies.get("csrftoken")

        # Extract some product URLs to use in Task 2 and Task 3
        catalog_response = self.client.get("/en/catalog/")
        if catalog_response.status_code == 200:
            soup = BeautifulSoup(catalog_response.text, "html.parser")
            # Find all product links (accounting for /en/ or /ar/ prefixes)
            links = soup.find_all("a", href=re.compile(r"^/[a-z]{2}/product/\d+/"))
            self.product_urls = list(set([link["href"] for link in links]))

    @task(6)
    def browse_generic(self):
        """
        Task 1 (Weight 6): Simulate generic browsing.
        """
        self.client.get("/en/")
        self.client.get("/en/catalog/")

    @task(3)
    def view_product(self):
        """
        Task 2 (Weight 3): Simulate high-priority sales traffic.
        """
        if self.product_urls:
            import random
            product_url = random.choice(self.product_urls)
            self.client.get(product_url, name="/[lang]/product/[id]/[slug]/")

    @task(1)
    def write_stress_cart(self):
        """
        Task 3 (Weight 1): Simulate database write stress.
        """
        if self.product_urls:
            import random
            product_url = random.choice(self.product_urls)
            
            # Extract language and product ID from the URL (e.g., /en/product/1/laptop-x/)
            match = re.search(r"^/([a-z]{2})/product/(\d+)/", product_url)
            if match:
                lang = match.group(1)
                product_id = match.group(2)
                
                # Fetch fresh CSRF token
                self.client.get(product_url, name="/[lang]/product/[id]/[slug]/")
                csrf_token = self.client.cookies.get("csrftoken")

                # POST to cart add endpoint
                self.client.post(
                    f"/{lang}/cart/add/{product_id}/",
                    data={
                        "quantity": 1,
                        "override": "False",
                        "csrfmiddlewaretoken": csrf_token
                    },
                    headers={"X-CSRFToken": csrf_token, "Referer": self.host + product_url},
                    name="/[lang]/cart/add/[id]/"
                )

# ==========================================
# HOW TO RUN AND ANALYZE THIS LOCUST TEST
# ==========================================
# 
# 1. Install Locust & BeautifulSoup4:
#    pip install locust beautifulsoup4
# 
# 2. Run the test via terminal:
#    locust -f locustfile.py --host=http://127.0.0.1:8000
# 
# 3. Access the Locust Dashboard:
#    Open your browser to http://localhost:8089
# 
# 4. Analysis Guidelines:
#    - Set 'Number of Users' to 500 and 'Spawn Rate' to 10 users/second.
#    - Monitor the "Failures" tab: 
#      * A Failure Rate > 1% under heavy load indicates the database is locking 
#        up or the server cannot handle the concurrency.
#    - Monitor the "Median Response Time" (50th percentile) and 95th percentile:
#      * Median Response Time > 500ms means the database queries 
#        (like `is_on_sale` and navbar caching) are poorly optimized.
#      * If POST requests (Task 3) cause spikes, we need to implement Redis caching 
#        or optimize the SQLite/PostgreSQL write concurrency.
# ==========================================
