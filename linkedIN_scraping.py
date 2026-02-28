#!/usr/bin/env python
# coding: utf-8

# ## With manual log-in but automatic Chrome opening

# In[1]:


import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time, re, json, os
import pandas as pd
from tabulate import tabulate
from datetime import datetime
import uuid
from selenium.webdriver.common.keys import Keys

# ---------- EXPERIENCE PARSER CLASS ----------
class ExperienceParser:
    def __init__(self, driver):
        self.driver = driver

    def clean_text(self, txt):
        return re.sub(r"(See more|Mostra|Vedi).*", "", txt or "", flags=re.I).strip()

    def extract_description(self, node):
        try:
            desc_divs = node.find_elements(
                By.XPATH,
                ".//div[contains(@class,'t-normal') and contains(@class,'t-black')] | "
                ".//div[contains(@class,'display-flex') and contains(@class,'align-items-center') and contains(@class,'t-normal')]"
            )
            seen_texts = set()
            texts = []
            for div in desc_divs:
                txt = div.text.strip()
                if txt and txt not in seen_texts:
                    seen_texts.add(txt)
                    texts.append(txt)
            return " ".join(texts)
        except:
            return ""

    def parse_from_main_profile(self):
        experiences = []
        try:
            exp_section = self.driver.find_element(
                By.XPATH,
                "//section[contains(@id,'experience') or .//h2[contains(.,'Experience')]]"
            )
            exp_items = exp_section.find_elements(By.XPATH, ".//li[contains(@class,'artdeco-list__item')]")
            for item in exp_items:
                try:
                    role_check = item.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span").text.strip()
                    if not role_check:
                        continue
                except:
                    continue

                try:
                    company = item.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span").text.strip()
                except:
                    company = ""

                subroles = item.find_elements(By.XPATH, ".//ul/li")
                valid_subroles = []
                for sub in subroles:
                    try:
                        sub.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span").text.strip()
                        valid_subroles.append(sub)
                    except:
                        continue

                if valid_subroles:
                    for sub in valid_subroles:
                        exp = self.extract_role(sub, parent_company=company)
                        experiences.append(exp)
                else:
                    exp = self.extract_role(item)
                    experiences.append(exp)
        except Exception as e:
            print("⚠️ Experience parsing error:", e)
        return experiences

    def parse_from_detail_page(self):
        experiences = []
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            time.sleep(2)
            exp_items = self.driver.find_elements(
                By.XPATH,
                "//li[contains(@class,'pvs-list__paged-list-item') and .//div[@data-view-name='profile-component-entity']]"
            )
            print(f"📊 Found {len(exp_items)} real experience items on detail page")
            for item in exp_items:
                try:
                    company_group = item.find_elements(
                        By.XPATH,
                        ".//div[@class='oBBCgurHfzlHZqJMFMnAhJzjZFLeAwaCYpns']//ul[contains(@class,'TQtryBgeHzFGDGLkqnUeDFeVWQtCnNDoJbgs')]"
                    )
                    if company_group:
                        company_name = self.extract_company_name(item)
                        subroles = company_group[0].find_elements(
                            By.XPATH, "./li[contains(@class,'pvs-list__paged-list-item')]"
                        )
                        for subrole in subroles:
                            exp = self.extract_role_from_detail(subrole, parent_company=company_name)
                            if exp and exp.get("job_title"):
                                experiences.append(exp)
                    else:
                        exp = self.extract_role_from_detail(item)
                        if exp and exp.get("job_title"):
                            experiences.append(exp)
                except Exception as e:
                    print(f"⚠️ Error parsing experience item: {e}")
                    continue
        except Exception as e:
            print(f"⚠️ Error parsing detail page: {e}")
        return experiences

    def extract_company_name(self, node):
        try:
            company_elem = node.find_element(
                By.XPATH,
                ".//div[contains(@class,'t-bold')]/span[@aria-hidden='true']"
            )
            return self.clean_text(company_elem.text)
        except:
            return ""

    def extract_role_from_detail(self, node, parent_company=""):
        try:
            role = node.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span[@aria-hidden='true']").text.strip()
        except:
            role = ""
        if not parent_company:
            try:
                company_elem = node.find_element(By.XPATH, ".//span[@class='t-14 t-normal']/span[@aria-hidden='true']")
                company_text = company_elem.text.strip()
                company = re.sub(r'\s*·\s*(Full-time|Part-time|Internship|Contract|Freelance).*', '', company_text)
            except:
                company = ""
        else:
            company = parent_company

        duration = ""
        try:
            duration_elem = node.find_element(By.XPATH, ".//span[contains(@class,'t-black--light')]/span[@class='pvs-entity__caption-wrapper']")
            duration = duration_elem.text.strip()
        except:
            pass
        start_date, end_date, still_works_here = self.parse_duration(duration)
        subject = self.extract_description(node)
        return {
            "job_title": self.clean_text(role),
            "company": self.clean_text(company),
            "subject": subject,
            "start_date": start_date,
            "end_date": end_date,
            "still_works_here": still_works_here
        }

    def extract_role(self, node, parent_company=""):
        try:
            role = node.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span").text.strip()
        except:
            role = ""
        try:
            company = node.find_element(By.XPATH, ".//span[contains(@class,'t-14') and not(contains(@class,'t-black--light'))]/span").text.strip()
        except:
            company = parent_company

        duration = ""
        light_spans = node.find_elements(By.XPATH, ".//span[contains(@class,'t-14') and contains(@class,'t-black--light')]/span")
        for span in light_spans:
            txt = span.text.strip()
            if re.search(r"\d{4}", txt):
                duration = txt
                break
        start_date, end_date, still_works_here = self.parse_duration(duration)
        subject = self.extract_description(node)
        return {
            "job_title": self.clean_text(role),
            "company": self.clean_text(company),
            "subject": subject,
            "start_date": start_date,
            "end_date": end_date,
            "still_works_here": still_works_here
        }

    def parse_duration(self, duration_text):
        start_date, end_date, still_works_here = "", "", False
        if not duration_text:
            return start_date, end_date, still_works_here
        m = re.search(r"([A-Za-zÀ-ÿ]{3,9} \d{4})\s*[-–]\s*([A-Za-zÀ-ÿ]{3,9} \d{4}|Present|Oggi|Aujourd'hui|Actualidad)?", duration_text, re.I)
        if m:
            start_date = m.group(1)
            end_date = m.group(2) if len(m.groups()) > 1 else ""
            if end_date and re.search(r"present|oggi|current|actualidad|maintenant", end_date, re.I):
                still_works_here = True
                end_date = ""
        else:
            years = re.findall(r"\d{4}", duration_text)
            if years:
                start_date = years[0]
                if len(years) > 1:
                    end_date = years[1]
        return start_date, end_date, still_works_here

# ---------- EDUCATION PARSER CLASS ----------
class EducationParser:
    def __init__(self, driver):
        self.driver = driver

    def clean_text(self, txt):
        txt = re.sub(r"(See more|Mostra|Vedi).*", "", txt or "", flags=re.I).strip()
        return txt.split("\n")[0].strip()

    def parse(self):
        education_list = []
        try:
            edu_section = self.driver.find_element(By.XPATH, "//section[@id='education' or .//h2[contains(.,'Education')]]")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edu_section)
            time.sleep(1)
            click_show_all_education(self.driver)
            for f in [0.25, 0.5, 0.75, 1.0]:
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{f});")
                time.sleep(0.5)

            edu_items = self.driver.find_elements(By.XPATH, "//li[contains(@class,'pvs-list__paged-list-item')]//div[@data-view-name='profile-component-entity']")
            print(f"📊 Found {len(edu_items)} education items")
            for item in edu_items:
                try:
                    institution = self.clean_text(item.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span[@aria-hidden='true']").text)
                except:
                    institution = ""
                try:
                    full_text = self.clean_text(item.find_element(By.XPATH, ".//span[contains(@class,'t-14') and contains(@class,'t-normal') and not(contains(@class,'t-black--light'))]/span[@aria-hidden='true']").text)
                    if "," in full_text:
                        qualification_type, subject = [x.strip() for x in full_text.split(",", 1)]
                    else:
                        qualification_type = full_text
                        subject = ""
                except:
                    qualification_type, subject = "", ""
                start_date, end_date, still_studying = "", "", False
                try:
                    dates_text = self.clean_text(item.find_element(By.XPATH, ".//span[contains(@class,'t-14') and contains(@class,'t-normal') and contains(@class,'t-black--light')]/span[@aria-hidden='true']").text)
                    start_date, end_date, still_studying = self.parse_duration(dates_text)
                except:
                    pass
                education_list.append({
                    "institution": institution,
                    "qualification_type": qualification_type,
                    "subject": subject,
                    "start_date": start_date,
                    "end_date": end_date,
                    "still_studying": still_studying
                })
            education_list.sort(key=lambda edu: int(re.search(r"\d{4}", edu["start_date"]).group(0)) if edu["start_date"] else 0, reverse=True)
        except Exception as e:
            print("⚠️ Education parsing error:", e)
        return education_list

    def parse_duration(self, duration_text):
        start_date, end_date, still_studying = "", "", False
        if not duration_text:
            return start_date, end_date, still_studying
        m = re.search(r"([A-Za-zÀ-ÿ]{3,9} \d{4}|\d{4})\s*[-–]\s*([A-Za-zÀ-ÿ]{3,9} \d{4}|\d{4}|Present|Oggi|Aujourd'hui|Actualidad)?", duration_text, re.I)
        if m:
            start_date = m.group(1)
            end_date = m.group(2) if len(m.groups()) > 1 else ""
            if end_date and re.search(r"present|oggi|current|actualidad|maintenant", end_date, re.I):
                still_studying = True
                end_date = ""
        else:
            years = re.findall(r"\d{4}", duration_text)
            if years:
                start_date = years[0]
                if len(years) > 1:
                    end_date = years[1]
        return start_date, end_date, still_studying

# ---------- VOLUNTEERING PARSER ----------
class VolunteeringParser:

    def __init__(self, driver):
        self.driver = driver

    def get_volunteering_section(self):
        """Safely locate the volunteering <section> by its <h2> heading."""
        try:
            h2 = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//h2[span[contains(., 'Volunteering')]]"
                ))
            )
            section = h2.find_element(By.XPATH, "./ancestor::section[1]")
            return section
        except Exception as e:
            print(f"⚠️ Could not locate Volunteering section: {e}")
            return None

    def expand_see_more(self, element):
        """Expand inline '…see more' elements inside a volunteering entry."""
        try:
            btn = element.find_element(
                By.XPATH,
                ".//button[contains(@class, 'inline-show-more-text__button')]"
            )
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.3)
        except:
            pass  # no see more present

    def parse_volunteering_items(self, li):
        """Extract volunteering entry fields."""
        try:
            role = li.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span").text.strip()
        except:
            role = ""

        try:
            org = li.find_element(By.XPATH, ".//span[@class='t-14 t-normal']/span").text.strip()
        except:
            org = ""

        try:
            dates = li.find_element(By.XPATH, ".//span[contains(@class,'caption-wrapper')]/span").text.strip()
        except:
            dates = ""

        try:
            cause = li.find_element(By.XPATH, ".//span[contains(., 'Welfare') or contains(.,'Environment') or contains(.,'Cause')]").text.strip()
        except:
            cause = ""

        # Expand the description if present
        self.expand_see_more(li)

        try:
            desc = li.find_element(
                By.XPATH,
                ".//div[contains(@class,'inline-show-more-text')]/span[1]"
            ).text.strip()
        except:
            desc = ""

        return {
            "Role": role,
            "Organization": org,
            "Dates": dates,
            "Cause": cause,
            "Description": desc
        }

    def parse(self):
        """Main parser entry point."""
        section = self.get_volunteering_section()
        if not section:
            return pd.DataFrame()

        items = section.find_elements(
            By.XPATH,
            ".//li[contains(@class,'artdeco-list__item')]"
        )

        data = []
        for li in items:
            data.append(self.parse_volunteering_items(li))

        return pd.DataFrame(data)

# ---------- PUBLICATIONS PARSER ----------
class PublicationsParser:

    def __init__(self, driver):
        self.driver = driver

    def click_show_all_publications(self):
        try:
            btn = self.driver.find_element(By.ID, "navigation-index-see-all-publication")
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)  # wait for new page to load
            print("✅ Clicked 'Show all publications' button")
            return True
        except:
            print("⚠️ 'Show all publications' button not found")
            return False

    def parse_single_publication(self, li):
        try:
            title = li.find_element(By.XPATH, ".//div[contains(@class,'t-bold')]/span").text.strip()
        except:
            title = ""

        try:
            publisher = li.find_element(
                By.XPATH,
                ".//span[@class='t-14 t-normal']/span"
            ).text.strip()
        except:
            publisher = ""

        # Sometimes the date is combined with publisher
        date = ""
        if "·" in publisher:
            parts = publisher.split("·")
            publisher = parts[0].strip()
            date = parts[1].strip() if len(parts) > 1 else ""
        else:
            try:
                date = li.find_element(
                    By.XPATH,
                    ".//span[contains(@class,'caption')]/span"
                ).text.strip()
            except:
                date = ""

        try:
            description = li.find_element(
                By.XPATH,
                ".//div[contains(@class,'inline-show-more-text')]/span[1]"
            ).text.strip()
        except:
            description = ""

        return {
            "Title": title,
            "Publisher": publisher,
            "Date": date,
            "Description": description
        }

    def parse(self):
        # First try to click "Show all publications"
        self.click_show_all_publications()

        # Wait for publication list to load
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//li[contains(@class,'pvs-list__paged-list-item')]"))
        )

        items = self.driver.find_elements(
            By.XPATH,
            "//li[contains(@class,'pvs-list__paged-list-item')]"
        )

        data = [self.parse_single_publication(li) for li in items]
        return pd.DataFrame(data)

# ---------- LANGUAGES PARSER ----------
class LanguagesParser:

    def __init__(self, driver):
        self.driver = driver

    def get_languages_section(self):
        try:
            h2 = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//h2[span[contains(., 'Languages')]]"
                ))
            )
            return h2.find_element(By.XPATH, "./ancestor::section[1]")
        except Exception as e:
            print(f"⚠️ Could not locate Languages section: {e}")
            return None

    def open_show_all_languages(self):
        try:
            btn = self.driver.find_element(By.ID, "navigation-index-see-all-languages")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.5)
            btn.click()
            time.sleep(2)
            return True
        except:
            return False

    def parse_language(self, li):
        try:
            lang = li.find_element(
                By.XPATH,
                ".//div[contains(@class,'t-bold')]/span[@aria-hidden='true']"
            ).text.strip()
        except:
            lang = ""

        try:
            proficiency = li.find_element(
                By.XPATH,
                ".//span[contains(@class,'pvs-entity__caption-wrapper') and @aria-hidden='true']"
            ).text.strip()
        except:
            proficiency = ""

        return {
            "Language": lang,
            "Proficiency": proficiency
        }

    def parse(self):
        # Open "Show all" first
        self.open_show_all_languages()

        # Wait for the list to appear
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//li[contains(@class,'pvs-list__paged-list-item')]"))
        )

        items = self.driver.find_elements(
            By.XPATH,
            "//li[contains(@class,'pvs-list__paged-list-item')]"
        )

        data = [self.parse_language(li) for li in items]
        return pd.DataFrame(data)

# ---------- SKILLS PARSER ----------
class SkillsParser:
    def __init__(self, driver):
        self.driver = driver

    def parse(self):
        skills = []
        # Each skill is a <li> with class 'pvs-list__paged-list-item'
        skill_items = self.driver.find_elements(
            By.XPATH,
            "//li[contains(@class,'pvs-list__paged-list-item')]"
        )

        for el in skill_items:
            try:
                # Skill name is in a span with aria-hidden="true" inside a div with t-bold and hoverable-link-text
                skill_name = el.find_element(
                    By.XPATH,
                    ".//div[contains(@class,'t-bold') and contains(@class,'hoverable-link-text')]/span[@aria-hidden='true']"
                ).text.strip()
                if skill_name:
                    skills.append({"Skill": skill_name})
            except:
                continue

        return pd.DataFrame(skills)
    
# ---------- CERTIFICATIONS PARSER ----------
    
class CertificationsParser:

    def __init__(self, driver):
        self.driver = driver

    def parse_single_cert(self, li):
        """Extract one certification item."""

        # --- Course name (title) ---
        try:
            course_name = li.find_element(
                By.XPATH,
                ".//div[contains(@class,'t-bold')]/span[@aria-hidden='true']"
            ).text.strip()
        except:
            course_name = ""

        # --- Certification type (issuer) ---
        try:
            certification_type = li.find_element(
                By.XPATH,
                ".//span[@class='t-14 t-normal']/span[@aria-hidden='true']"
            ).text.strip()
        except:
            certification_type = ""

        # --- Date attained (issue date) ---
        try:
            date_attained = li.find_element(
                By.XPATH,
                ".//span[contains(@class,'t-black--light')]/span[@aria-hidden='true']"
            ).text.replace("Issued", "").strip()
        except:
            date_attained = ""

        # --- Details (skills inside certification OR credential link OR description) ---
        # Priority: skills > credential URL
        try:
            details_raw = li.find_element(
                By.XPATH,
                ".//strong[contains(.,'Skills')]/parent::span"
            ).text.strip()
            details = details_raw.replace("Skills:", "").strip()
        except:
            try:
                cred_button = li.find_element(
                    By.XPATH,
                    ".//a[contains(@aria-label,'Show credential')]"
                )
                details = cred_button.get_attribute("href")
            except:
                details = ""

        return {
            "course_name": course_name,
            "certification_type": certification_type,
            "date_attained": date_attained,
            "details": details
        }

    def parse(self):
        # Try to open the certifications section first
        section_exists = click_show_all_certifications(self.driver)
        if not section_exists:
            print("⚠️ Certifications section not found, skipping scraping.")
            return pd.DataFrame()  # Return empty if section doesn't exist

        # Wait for certification items to appear
        try:
            WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//li[contains(@class,'pvs-list__paged-list-item')]"
                ))
            )
        except TimeoutException:
            print("⚠️ No certification items found on detail page")
            return pd.DataFrame()

        items = self.driver.find_elements(
            By.XPATH,
            "//li[contains(@class,'pvs-list__paged-list-item')]"
        )

        # Parse each certification
        return pd.DataFrame([self.parse_single_cert(li) for li in items])

# ---------- Helper functions ----------
def safe_click_element(driver, element, method="javascript"):
    try:
        if method == "javascript":
            driver.execute_script("arguments[0].click();", element)
        elif method == "scroll_and_click":
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            element.click()
        elif method == "action_chains":
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            actions.move_to_element(element).click().perform()
        return True
    except Exception as e:
        print(f"⚠️ Click method '{method}' failed: {e}")
        return False

def click_show_all_experiences(driver):
    selectors = [
        "//a[@id='navigation-index-see-all-experiences']",
        "//a[contains(@href,'/details/experience')]",
        "//a[contains(.,'Show all') and contains(.,'experience')]",
        "//div[contains(@class,'pvs-list__footer-wrapper')]//a[contains(@href,'experience')]"
    ]
    for selector in selectors:
        try:
            element = driver.find_element(By.XPATH, selector)
            print(f"✅ Found 'Show all experiences' button")
            for method in ["javascript", "scroll_and_click", "action_chains"]:
                if safe_click_element(driver, element, method):
                    print(f"✅ Clicked using {method}")
                    return True
                time.sleep(0.5)
        except:
            continue
    return False

def click_show_all_education(driver):
    try:
        element = driver.find_element(By.ID, "navigation-index-see-all-education")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", element)
        time.sleep(2)
        print("✅ Clicked 'Show all education' button")
        return True
    except:
        print("⚠️ No 'Show all education' button found")
        return False

def click_all_show_buttons(driver):
    time.sleep(1)
    buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Show all') or contains(text(),'See all') or contains(@aria-label,'Show all') or contains(@aria-label,'See all')]")
    for btn in buttons:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1.5)
        except ElementClickInterceptedException:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1.5)
            except:
                continue

def safe_find_section(driver, xpaths, wait_time=3):
    """Try multiple XPaths to find a section safely."""
    for xp in xpaths:
        try:
            section = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, xp))
            )
            return section
        except TimeoutException:
            continue
    return None

def go_to_skills_detail_page(driver):
    try:
        btn = driver.find_element(
            By.XPATH,
            "//a[contains(@href,'details/skills') and contains(.,'Show all')]"
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)
        print("✅ Entered skills detail page")
        return True
    except Exception as e:
        print("⚠️ Could not open the skills detail page:", e)
        return False

def click_show_all_certifications(driver):
    selectors = [
        "//a[@id='navigation-index-see-all-certifications']",
        "//a[contains(@href,'details/certifications')]",
        "//a[contains(.,'Show all') and contains(.,'certifications')]"
    ]
    for selector in selectors:
        try:
            element = driver.find_element(By.XPATH, selector)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", element)
            time.sleep(2)
            print("✅ Entered certifications detail page")
            return True
        except:
            continue
    print("⚠️ No 'Show all certifications' button found")
    return False

# ---------- UTILITY FUNCTIONS ----------
def classify_skill(skill):
    # Example: simple classification
    technical_keywords = ["Python", "Java", "SQL", "Excel", "Power BI", "AWS", "Tableau", "JavaScript"]
    if any(k.lower() in skill.lower() for k in technical_keywords):
        return "technical"
    else:
        return "soft"

# ---------- CONFIG ----------
PROFILE_URL = "https://www.linkedin.com/in/eliana-di-lodovico-570171192/en"
WAIT_TIMEOUT = 300

# ---------- LAUNCH BROWSER ----------
options = uc.ChromeOptions()
options.add_argument("--start-maximized")
driver = uc.Chrome(options=options)
driver.get("https://www.linkedin.com/login")
print("Please log in manually in the browser window...")

# Wait for manual login
start = time.time()
while True:
    time.sleep(1)
    if any(c.get("name") == "li_at" for c in driver.get_cookies()):
        print("✅ Login detected — proceeding.")
        break
    if time.time() - start > WAIT_TIMEOUT:
        input("⚠️ Timeout reached. Press Enter if already logged in.")
        break

# ---------- NAVIGATE TO PROFILE ----------
driver.get(PROFILE_URL)
time.sleep(2)

# ---------- EXPAND ALL BUTTONS ----------
expanders = [
    "//button[contains(.,'See more')]",
    "//button[contains(.,'Mostra')]",
    "//button[contains(@aria-label,'See more')]"
]
for xp in expanders:
    try:
        el = driver.find_element(By.XPATH, xp)
        driver.execute_script("arguments[0].scrollIntoView(true);", el)
        time.sleep(0.3)
        el.click()
        time.sleep(0.7)
    except:
        continue

click_all_show_buttons(driver)

# Scroll to load all content
for f in [0.25, 0.5, 0.75, 1.0]:
    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{f});")
    time.sleep(0.7)

# ---------- BASIC PROFILE INFO ----------
def try_selectors(selectors):
    for by, sel in selectors:
        try:
            el = driver.find_element(by, sel)
            txt = el.text.strip()
            if txt:
                return txt
        except:
            pass
    return None

name = try_selectors([(By.CSS_SELECTOR, "h1.text-heading-xlarge"), (By.XPATH, "//main//h1")])
headline = try_selectors([(By.CSS_SELECTOR, "div.text-body-medium.break-words")])
location = try_selectors([(By.CSS_SELECTOR, "span.text-body-small.inline.t-black--light.break-words")])

# About / Bio
bio = ""
try:
    about_el = driver.find_element(By.XPATH, "//div[contains(@class,'inline-show-more-text')]//span[@aria-hidden='true']")
    bio = about_el.text.strip()
except:
    bio = ""

# Profile picture
output_dir = "linkedin_data"
os.makedirs(output_dir, exist_ok=True)

profile_pic_path = ""

try:
    img_el = driver.find_element(By.XPATH, "//img[contains(@class,'profile-photo-edit__preview')]")
    img_url = img_el.get_attribute("src") or ""
    if img_url:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"profile_pic_{ts}.jpeg"
        profile_pic_path = os.path.join(output_dir, img_filename)

        # Use cookies & headers for LinkedIn access
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(img_url, stream=True, headers=headers, cookies=cookies, timeout=10)

        if response.status_code == 200:
            with open(profile_pic_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"✅ Profile picture saved: {profile_pic_path}")
        else:
            print(f"⚠️ Failed to download profile pic, status code: {response.status_code}")
except Exception as e:
    print(f"⚠️ Could not save profile picture: {e}")

# Contact info / email
email = ""
contact_selectors = [
    "//a[contains(@href,'overlay/contact-info')]",
    "//a[contains(@id,'contact-info')]",
    "//button[contains(.,'Contact info')]",
    "//a[@data-control-name='contact_see_more']"
]

def open_contact_modal(driver):
    for sel in contact_selectors:
        try:
            el = driver.find_element(By.XPATH, sel)
            try:
                el.click()
            except:
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                driver.execute_script("arguments[0].click();", el)
            return True
        except:
            continue
    return False

try:
    opened = open_contact_modal(driver)
    if opened:
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//a[starts-with(@href,'mailto:')]"))
            )
            email_el = driver.find_element(By.XPATH, "//a[starts-with(@href,'mailto:')]")
            email = email_el.get_attribute("href").replace("mailto:", "").strip()
        except:
            email = ""
        try:
            dismiss = driver.find_element(By.XPATH, "//button[@aria-label='Dismiss' or @aria-label='Close']")
            try:
                dismiss.click()
            except:
                driver.execute_script("arguments[0].click();", dismiss)
        except:
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except:
                pass
except:
    email = ""

# ---------- PROFILE DATAFRAME ----------
first_name, surname = "", ""
if name:
    parts = name.split()
    if len(parts) >= 2:
        first_name = parts[0]
        surname = " ".join(parts[1:])
    else:
        first_name = name

id = str(uuid.uuid4())
cv_link = ""
user_type = ""

profile = pd.DataFrame([{
    "id": id,
    "first_name": first_name,
    "surname": surname,
    "email": email,
    "profile_pic": "",  # keep empty, picture code commented
    "cv_link": cv_link,
    "bio": bio,
    "user_type": user_type
}])

# ---------- EXPERIENCE ----------
parser = ExperienceParser(driver)
experience = []
try:
    if click_show_all_experiences(driver):
        time.sleep(3)
        for f in [0.25, 0.5, 0.75, 1.0]:
            driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{f});")
            time.sleep(0.5)
        experience = parser.parse_from_detail_page()
        if not experience:
            driver.get(PROFILE_URL)
            time.sleep(2)
            experience = parser.parse_from_main_profile()
    else:
        driver.get(PROFILE_URL)
        time.sleep(2)
        experience = parser.parse_from_main_profile()
except:
    driver.get(PROFILE_URL)
    time.sleep(2)
    experience = parser.parse_from_main_profile()

work_experience = pd.DataFrame(experience)
work_experience["we_id"] = [str(uuid.uuid4()) for _ in range(len(work_experience))]
work_experience["first_name"] = first_name
work_experience["surname"] = surname
work_experience["subject"] = work_experience["subject"].apply(lambda x: " ".join(dict.fromkeys(x.split("\n"))).strip())
work_experience["candidate_id"] = ""
work_experience = work_experience[['we_id','first_name','surname','job_title','company','subject','start_date','end_date','still_works_here','candidate_id']]

# ---------- EDUCATION ----------
driver.get(PROFILE_URL)
time.sleep(2)
edu_parser = EducationParser(driver)
education = edu_parser.parse()
education_history = pd.DataFrame(education)
education_history["ed_id"] = [str(uuid.uuid4()) for _ in range(len(education_history))]
education_history["first_name"] = first_name
education_history["surname"] = surname
education_history["candidate_id"] = ""
education_history = education_history[['ed_id','first_name','surname','institution','qualification_type','subject','start_date','end_date','still_studying','candidate_id']]

# ---------- VOLUNTEERING ----------
driver.get(PROFILE_URL)
time.sleep(2)
vol_parser = VolunteeringParser(driver)
volunteering = vol_parser.parse()
volunteering_experience = pd.DataFrame(volunteering)

# ---------- PUBLICATIONS ----------
driver.get(PROFILE_URL)
time.sleep(2)
pub_parser = PublicationsParser(driver)
publications = pub_parser.parse()
publications_df = pd.DataFrame(publications)

# ---------- LANGUAGES ----------
driver.get(PROFILE_URL)
time.sleep(2)
lang_parser = LanguagesParser(driver)
languages = lang_parser.parse()
languages_df = pd.DataFrame(languages)

# ---------- SKILLS ----------
driver.get(PROFILE_URL)
time.sleep(2)
go_to_skills_detail_page(driver)  # Opens the "Show all skills" page
time.sleep(2)

# Scroll to load all skills dynamically
for f in [0.25, 0.5, 0.75, 1.0]:
    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{f});")
    time.sleep(0.75)

# ---------- EXTRACT SKILLS ----------
skills_parser = SkillsParser(driver)
skills_df_raw = skills_parser.parse()

# Extract only skill names
skill_names = skills_df_raw["Skill"].tolist() if not skills_df_raw.empty else []

# ---------- CLASSIFY SKILLS ----------
technical_skills = []
soft_skills = []

for skill in skill_names:
    if classify_skill(skill) == "technical":
        technical_skills.append(skill)
    else:
        soft_skills.append(skill)

# ---------- BUILD DATAFRAMES ----------
technical_skills_df = pd.DataFrame({"skill_name": technical_skills})
if not technical_skills_df.empty:
    technical_skills_df.insert(0, "tech_skill_id", [str(uuid.uuid4()) for _ in range(len(technical_skills_df))])
    technical_skills_df["value"] = ""

soft_skills_df = pd.DataFrame({"skill_name": soft_skills})
if not soft_skills_df.empty:
    soft_skills_df.insert(0, "soft_skill_id", [str(uuid.uuid4()) for _ in range(len(soft_skills_df))])
    soft_skills_df["value"] = ""

# ---------- CERTIFICATIONS ----------
try:
    cert_parser = CertificationsParser(driver)
    certifications = cert_parser.parse()

    if not certifications.empty:
        certifications["certif_id"] = [str(uuid.uuid4()) for _ in range(len(certifications))]
        certifications["first_name"] = first_name
        certifications["surname"] = surname
        certifications["candidate_id"] = ""  # to be filled later

        # Reorder columns EXACTLY as you specified
        certifications = certifications[[
            "certif_id",
            "first_name",
            "surname",
            "course_name",
            "certification_type",
            "date_attained",
            "details",
            "candidate_id"
        ]]

except Exception as e:
    print("⚠️ Certification parsing failed:", e)
    certifications = pd.DataFrame(columns=[
        "certif_id", "first_name", "surname",
        "course_name", "certification_type",
        "date_attained", "details", "candidate_id"
    ])

# ---------- DISPLAY OUTPUT ----------
print("\n=== LINKEDIN PROFILE ===")
print(f"👤 Name: {name}")
print(f"💼 Headline: {headline}")
print(f"📍 Location: {location}")
if bio:
    print(f"📝 About: {bio}")
if email:
    print(f"📧 Email: {email}")

if not profile.empty:
    print("\n=== PROFILE ===")
    print(tabulate(profile, headers='keys', tablefmt='fancy_grid', showindex=False))
if not work_experience.empty:
    print("\n=== WORK EXPERIENCE ===")
    print(tabulate(work_experience, headers='keys', tablefmt='fancy_grid', showindex=False))
if not education_history.empty:
    print("\n=== EDUCATION HISTORY ===")
    print(tabulate(education_history, headers='keys', tablefmt='fancy_grid', showindex=False))
if not volunteering_experience.empty:
    print("\n=== VOLUNTEERING EXPERIENCE ===")
    print(tabulate(volunteering_experience, headers='keys', tablefmt='fancy_grid', showindex=False))
if not publications_df.empty:
    print("\n=== PUBLICATIONS ===")
    print(tabulate(publications_df, headers='keys', tablefmt='fancy_grid', showindex=False))
if not languages_df.empty:
    print("\n=== LANGUAGES ===")
    print(tabulate(languages_df, headers='keys', tablefmt='fancy_grid', showindex=False))
if not soft_skills_df.empty:
    print("\n=== SOFT SKILLS ===")
    print(tabulate(soft_skills_df, headers='keys', tablefmt='fancy_grid', showindex=False))
if not technical_skills_df.empty:
    print("\n=== TECHNICAL SKILLS ===")
    print(tabulate(technical_skills_df, headers='keys', tablefmt='fancy_grid', showindex=False))
if not certifications.empty:
    print("\n=== CERTIFICATIONS ===")
    print(tabulate(certifications, headers='keys', tablefmt='fancy_grid', showindex=False))

# ---------- SAVE DATAFRAMES TO CSV ----------
output_dir = "linkedin_data"
os.makedirs(output_dir, exist_ok=True)

profile.to_csv(os.path.join(output_dir, "profile.csv"), index=False)
work_experience.to_csv(os.path.join(output_dir, "work_experience.csv"), index=False)
education_history.to_csv(os.path.join(output_dir, "education_history.csv"), index=False)
volunteering_experience.to_csv(os.path.join(output_dir, "volunteering_experience.csv"), index=False)
publications_df.to_csv(os.path.join(output_dir, "publications.csv"), index=False)
languages_df.to_csv(os.path.join(output_dir, "languages.csv"), index=False)
soft_skills_df.to_csv(os.path.join(output_dir, "soft_skills.csv"), index=False)
technical_skills_df.to_csv(os.path.join(output_dir, "technical_skills.csv"), index=False)
certifications.to_csv(os.path.join(output_dir, "certifications.csv"), index=False)

print(f"\n✅ All dataframes saved to folder: {output_dir}")

print("Current working directory:", os.getcwd())

# ---------- CLEAN EXIT ----------
driver.quit()