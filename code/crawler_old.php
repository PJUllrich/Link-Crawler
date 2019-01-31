<?php
header("Content-Type: text/plain");

// Please change the url below to the url of the main page that should be checked. Don't forget to add "http:\\" or "https:\\".
$rootPage = "http://www.rug.nl";

// Please specify a path to save a text file containing the broken links.
$file = fopen("../../Desktop/Brokenlinks.txt", "x");

// Please indicate whether you want to see the output of the running script
$seeOutput = true;

// We want to filter some links out based on specific keywords (e.g. php commands like "login?" or "?lang")
// You can write every keyword you want to use for the filter into this array.
// I only wrote some default keywords in here, but this array can be configured for your personal needs.
$filterKeys = array(
    "login?",
    "?lang",
    "javascript:",
    "!rss",
    "?print",
    ".pdf",
    "mailto:"
);

// Here we implement a history, so that checked links are not checked again.
$history = array();
$history[] = $rootPage;

$runNr = 1; // Running number to create unique object names.


class Page {
    var $ownUrl;
    var $linksOnPage;
    var $completeLinks;
    var $ownStatus;
    var $parentUrl;

    function Page($parent, $url, $goFurther) {
        // Variable implementation.
        global $history;
        global $rootPage;
        global $file;
        global $seeOutput;
        global $runNr;

        // Set the object-specific info.
        $this->parentUrl = $parent;
        $this->ownUrl = $url;

        // Now comes the request to read out the html of the page.
        $request = curl_init($url);             // A new http-request is implemented.
        curl_setopt_array($request, array(      // The options for this request are set. The options are explained on http://php.net/manual/en/function.curl-setopt.php
            CURLOPT_MAXREDIRS => 8,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 10
        ));

        $output = curl_exec($request);          // The html is saved in $output
        $this->ownStatus = curl_getinfo($request, CURLINFO_HTTP_CODE); // The page status is retrieved from the transaction protocoll
        curl_close($request);

        // I first used the following alternative to cURL, but it needs the installation of the PECL extension from http://pecl.php.net/package/pecl_http
        // I decided on using cURL instead, because the installation of the PECL extension didn't quite work for me and might cause problems if this script is used a different machine.
        /*$output = new HttpRequest($url);
        $output->setOptions(array('redirect' => 8));
        $output->send();
        $this->ownStatus = $output->getResponseCode();*/

        // If you didn't want to see the output in the console, the following code is not executed.
        if ($seeOutput == true && KeyFilter($this->ownUrl)) {
            echo ($this->parentUrl." ");
            echo ($this->ownUrl." ");
            echo ($this->ownStatus."\n");
        }

        // If the page is available, lies within the root page, and passes the key filter,
        // the script searches in the page html for links, filters them, and creates new objects for every link to check them.
        if ($this->ownStatus == 200 && $goFurther == true && KeyFilter($this->ownUrl)) {
            $matches = array();
            preg_match_all('/<a.+href="(.+)"/iU', $output, $matches);   // Reads out all links on the page

            if (!empty($matches)) {

                // Now we will streamline the links first to avoid multiple checks of the same page.
                array_walk($matches[1], "DeleteEndSlash");                 // Erase the "/" at the end
                $woDup = array_unique($matches[1]);                         // Delete duplicates
                $this->linksOnPage = array_filter($woDup, "LinkFilter");    // Delete # and links that redirect to the parent page.

                // Now we will write out the links in full. E.g. "/bibliotheek" becomes "http://www.rug.nl/bibliotheek"
                foreach ($this->linksOnPage as $link) {
                    if ($link[0] == "/") {
                        $this->completeLinks[] = $rootPage . $link;
                    } else if (strpos($link, "http") === false) {
                        $this->completeLinks[] = $rootPage . "/" . $link;
                    } else {
                        $this->completeLinks[] = $link;
                    }
                }

                // Next, new objects are created for every link on the page if the page was not visited yet.
                foreach ($this->completeLinks as $link) {
                    if (!in_array($link, $history)) {
                        $history[] = $link;
                        if (strpos($link, $rootPage) !== false) {
                            ${'page' . $runNr} = new Page($this->ownUrl, $link, true);
                            $runNr++;
                        } else {
                            // If a link directs to a page not hosted by the root page (e.g. www.youtube.com),
                            // then only the availability of the page is checked, but the script stops there.
                            ${'page' . $runNr} = new Page($this->ownUrl, $link, false);
                            $runNr++;
                        }
                    }
                }
            }

        // If the page is not available, but the link passes the key filter,
        // the script writes the parent link, the broken link, and the status in the document.
        } else if ($this->ownStatus != 200 && KeyFilter($this->ownUrl)) {
            fwrite($file, $this->parentUrl . " " . $this->ownUrl . " " . $this->ownStatus . "\n");
        }
    }
}

function DeleteEndSlash(&$link) {
    $link = rtrim($link, "/");
}

// This function checks whether a link contains the key terms specified before.
function KeyFilter($link) {
    global $filterKeys;
    $j = 0;
    foreach ($filterKeys as $key) {
        if (strpos($link, $key) !== false) {$j++;}
    }
    return($j == 0 ? true : false);
}

function LinkFilter($link) {
    if ($link == "" || $link[0] == "#"){
        return false;
    } else {
        return true;
    }
}

// With this first creation of an object, the whole process begins.
$page = new Page($rootPage, $rootPage, true);
?>
