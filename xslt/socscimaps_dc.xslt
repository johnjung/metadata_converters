<xsl:stylesheet version="2.0" exclude-result-prefixes="lc xs" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:lc="http://www.loc.gov/MARC21/slim" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <!-- MARCXML to Dublin Core transform for the Social Scientists Map Series.
         see: https://catalog.lib.uchicago.edu/vufind/Search/Results?type=SeriesBrowse&lookfor=%22Social%20scientists%20map%20Chicago%22 

         NOTES:
         creator:
         the spec says to use the 100 field. Should subfields a-z be
         concatenated together, or just use subfield a?
         
         dates:
         dates are encoded in a variety of formats:
         1924., 1925., 1927.  1935., 1943., [192-?], [192-], [1923], [1924],
         [1925], [1929], [193-?], [1930-1935], [1932], [1933], [1936], [1940?],
         [1943], [1957?], [approximately 1932], [approximately 1933], [between
         1908 and 1919?], [between 1933 and 1939], ©1926.

         of the dates above, only one is definitively out of copyright. Beacuse
         of that I assign the rights statement based on the identifier, and not
         by parsing dates. 

         identifier:
         the first record in the series contains several 856's with subfield u.
         should I use a single identifer for all of these records? -->

    <!-- -->
    <xsl:template match="@*|node()">
        <xsl:apply-templates select="@*|node()"/>
    </xsl:template>

    <!-- -->
    <xsl:template match="lc:controlfield|lc:leader|lc:subfield" />

    <!-- -->
    <xsl:template match="lc:collection">
        <records>
            <xsl:apply-templates select="*"/>
        </records>
    </xsl:template>

    <!-- -->
    <xsl:template match="lc:record">
        <record>
            <xsl:apply-templates select="*"/>
            <dc:language>en</dc:language>
        </record>
    </xsl:template>

    <!-- dc:coverage
         return one element for each 651 subfields a or z, where second indicator = 7 and subfield $2 = 'fast' -->
    <xsl:template match="lc:datafield[@tag='651' and @ind2='7' and lc:subfield[@code='2' and text()='fast']]/lc:subfield[@code='a' or @code='z']">
        <dc:coverage>
            <xsl:value-of select="."/>
        </dc:coverage>
    </xsl:template>

    <!-- dc:creator
         return one element for each 100 subfield a-z -->
    <xsl:template match="lc:datafield[@tag='100']/lc:subfield[@code = 'a']">
        <dc:creator>
            <xsl:value-of select="."/>
        </dc:creator>
    </xsl:template>

    <!-- dc:date 
         return one element, the first of either 260 subfield c or 264 subfield c  -->
    <xsl:template match="(lc:datafield[@tag='260' or @tag='264']/lc:subfield[@code='c'])[1]">
        <dc:date>
            <xsl:value-of select="."/>
        </dc:date>
    </xsl:template>

    <!-- dc:description
         return one element, all 500 subfields concatenated together -->
    <xsl:template match="lc:datafield[@tag='500' and lc:subfield[matches(@code, '[a-z]')]][1]">
        <dc:description>
            <xsl:for-each select="parent::lc:record/lc:datafield[@tag='500']/lc:subfield[matches(@code, '[a-z]')]">
                <xsl:if test="position() &gt; 1">
                    <xsl:text>&#160;</xsl:text>
                </xsl:if>
                <xsl:value-of select="."/>
            </xsl:for-each>
        </dc:description>
    </xsl:template>

    <!-- dc:extent 
         return one element for each 300 subfield c -->
    <xsl:template match="lc:datafield[@tag='300']/lc:subfield[@code='c']">
        <dc:extent>
            <xsl:value-of select="."/>
        </dc:extent>
    </xsl:template>

    <!-- dc:identifier 
         return one element for each 856 subfield u -->
    <xsl:template match="lc:datafield[@tag='856']/lc:subfield[@code='u']">
        <dc:identifier>
            <xsl:value-of select="."/>
        </dc:identifier>
        <xsl:call-template name="rights">
            <xsl:with-param name="identifier" select="."/>
        </xsl:call-template>
    </xsl:template>

    <!-- dc:publisher 
         return one element, the first of either 260 subfield c or 264 subfield b -->
    <xsl:template match="(lc:datafield[@tag='260' or @tag='264']/lc:subfield[@code='b'])[1]">
        <dc:publisher>
            <xsl:value-of select="."/>
        </dc:publisher>
    </xsl:template>

    <!-- dc:rights
         choose an appropriate rights statement based on the item. -->
    <xsl:template name="rights">
        <xsl:param name="identifier" />
        <xsl:choose>
            <xsl:when test="$identifier = 'http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-2N3E51-1908-S2'">
                <dc:rights>https://creativecommons.org/publicdomain/zero/1.0/</dc:rights>
            </xsl:when>
            <xsl:otherwise>
                <dc:rights>https://rightsstatements.org/page/InC/1.0/?language=en</dc:rights>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- dc:subject
         return one element for each 650 with a second indicator = 7 and subfield 2 = 'fast' -->
    <xsl:template match="lc:datafield[@tag='650' and @ind2='7' and lc:subfield[@code = '2' and text() = 'fast']]/lc:subfield[matches(@code, '[a-z]')]">
        <dc:subject>
            <xsl:value-of select="."/>
        </dc:subject>
    </xsl:template>
  
    <!-- dc:title
         return one element, 245 subfields a-z concatenated together -->
    <xsl:template match="lc:datafield[@tag='245' and lc:subfield[matches(@code, '[a-z]')]]">
        <dc:title>
            <xsl:for-each select="lc:subfield[matches(@code, '[a-z]')]">
                <xsl:if test="position() &gt; 1">
                    <xsl:text>&#160;</xsl:text>
                </xsl:if>
                <xsl:value-of select="."/>
            </xsl:for-each>
        </dc:title>
    </xsl:template>

    <!-- dc:type
         return one element for each 336 subfield -->
    <xsl:template match="lc:datafield[@tag='336']/lc:subfield[@code='a']">
        <dc:type>
            <xsl:value-of select="."/>
        </dc:type>
    </xsl:template>
</xsl:stylesheet>
