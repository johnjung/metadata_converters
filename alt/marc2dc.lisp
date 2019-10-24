'(
    :TEMPLATE 
    (
        :EXCLUDE                  ()
        :FILTER                   ()
        :INDICATOR1_RE            "."
        :INDICATOR2_RE            "."
        :JOIN_SUBFIELDS           t
        :JOIN_FIELDS              nil
        :RETURN_FIRST_RESULT_ONLY nil
        :SUBFIELD_RE              "(a-z)"
        :TAG_RE                   ".*"
    )
    :CROSSWALK
    (
        :dc_accessRights
        (
            :TAG_RE               "506"
        )
        :dc_contributor
        (
            :TAG_RE               "700|710"
            :SUBFIELD_RE          "a"
        )
        :dc_coverage
        (
            :TAG_RE               "651"
            :SUBFIELD_RE          "(az)"
            :FILTER (
                :SUBFIELD_RE      "2"
                :VALUE_RE         "^fast$"
            )
        )
        :dc_creator
        (
            (
                :TAG_RE           "100|110|111"
            )
            ( 
                :TAG_RE           "533"
                :SUBFIELD_RE      "c"
            )
        )
        :dc_date
        (
            :TAG_RE               "533"
            :SUBFIELD_RE          "d"
        )
        :dc_dateCopyrighted
        (
            :TAG_RE               "264"
            :SUBFIELD_RE          "c"
            :INDICATOR1_RE        "4"
        )
        :dc_description
        (
            :TAG_RE               "500|538"
            :JOIN_FIELDS          t
        )
        :dc_extent
        (
            :TAG_RE               "300"
            :SUBFIELD_RE          "(ac)"
        )
        :dc_format
        (
            :TAG_R                "255"
            :SUBFIELD_RE          "(ab)"
        )
        :dc_hasFormat
        (
            :TAG_RE               "533|776"
            :SUBFIELD_RE          "a"
        )
        :dc_identifier
        (
            (
                :TAG_RE           "856"
                :SUBFIELD_RE      "u"
                :RETURN_FIRST_RESULT_ONLY t
            )
            (
                :TAG_RE           "02(0-9)"
            )
        )
        :dc_isPartOf
        (
            (
                :TAG_RE           "533"
                :SUBFIELD_RE      "f"
            )
            (
                :TAG_RE           "830"
            )
        )
        :dc_language
        (
            :TAG_RE               "034"
        )
        :dc_medium
        (
            :TAG_RE              "338"
        )
        :dc_relation
        (
            :TAG_RE              "730"
            :SUBFIELD_RE         "a"
        )
        :dc_subject
        (
            (
                :TAG_RE          "050"
            )
            (   
                :TAG_RE          "650"
                :SUBFIELD_RE     "(ax)"
            )
        )
        :dc_title
        (
            (
                :TAG_RE          "130|240"
            )
            (
                :TAG_RE          "245"
                :SUBFIELD_RE     "(ab)"
            )
        )
        :dc_type
        (
            (
                :TAG_RE          "336"
            )
            (
                :TAG_RE          "60(01)"
                :SUBFIELD_RE     "v"
            )
            (
                :TAG_RE          "655"
                :FILTER (
                    :SUBFIELD_RE "2"
                    :VALUE_RE    "^fast$"
                )
            )
        )
        :dcterms_alternative
        (
            :TAG_RE              "246"
        )
        :dcterms_isssued
        (
            (
                :TAG_RE          "260"
                :SUBFIELD_RE     "c"
            )
            (
                :TAG_RE          "264"
                :SUBFIELD_RE     "c"
                :INDICATOR2_RE   "1"
            )
        )
        :dcterms_location
        (
            (
                :TAG_RE          "260"
                :SUBFIELD_RE     "a"
            )
            (
                :TAG_RE          "264"
                :SUBFIELD_RE     "a"
                :INDICATOR2_RE   "1"
            )
            (
                :TAG_RE          "533"
                :SUBFIELD_RE     "b"
            )
        )
        :dcterms_publisher
        (
            (
                :TAG_RE          "260"
                :SUBFIELD_RE     "b"
            )
            (
                :TAG_RE          "264"
                :SUBFIELD_RE     "b"
                :INDICATOR2_RE   "1"
            )
        )
    )
)



















;;;'(
;;;    ("template" . (
;;;        ("exclude"                  . ()     )
;;;        ("filter"                   . ()     )
;;;        ("indicator1_re"            . "."    )
;;;        ("indicator2_re"            . "."    )
;;;        ("join_subfields"           . t      )
;;;        ("join_fields"              . nil    )
;;;        ("return_first_result_only" . nil    )
;;;        ("subfield_re"              . "(a-z)")
;;;        ("tag_re"                   . ".*"   )
;;;    ))
;;;    ("crosswalk" . (
;;;        ("dc:accessRights" . (
;;;            (
;;;                ("tag_re" . "506")
;;;            )
;;;        ))
;;;        ("dc:contributor" . (
;;;            (
;;;                ("tag_re" . "700|710")
;;;                ("subfield_re" . "a")
;;;            )
;;;        ))
;;;        ("dc:coverage" . (
;;;            (
;;;                ("tag_re" . "651")
;;;                ("sub.ield_re" . "(az)")
;;;                ("filter" . (
;;;                    ("subfield_re" . "2")
;;;                    ("value_re" . "^fast$")
;;;                ))
;;;            )
;;;        ))
;;;        ("dc:creator" . (
;;;            (
;;;                ("tag_re" . "100|110|111")
;;;            )
;;;            ( 
;;;                ("tag_re" . "533")
;;;                ("subfield_re" . "c")
;;;            )
;;;        ))
;;;        ("dc:date" . (
;;;            (
;;;                ("tag_re" . "533")
;;;                ("subfield_re" . "d")
;;;            )
;;;        ))
;;;        ("dc:dateCopyrighted" . (
;;;            (
;;;                ("tag_re" . "264")
;;;                ("subfield_re" . "c")
;;;                ("indicator1_re" . "4")
;;;            )
;;;        ))
;;;        ("dc:description" . (
;;;            (
;;;                ("tag_re" . "500|538")
;;;                ("join_fields" . t)
;;;            )
;;;        ))
;;;        ("dc:extent" . (
;;;            (
;;;                ("tag_re" . "300")
;;;                ("subfield_re" . "(ac)")
;;;            )
;;;        ))
;;;        ("dc:format" . (
;;;            (
;;;                ("tag_re" . "255")
;;;                ("subfield_re" . "(ab)")
;;;            )
;;;        ))
;;;        ("dc:hasFormat" . (
;;;            (
;;;                ("tag_re" . "533|776")
;;;                ("subfield_re" . "a")
;;;            )
;;;        ))
;;;        ("dc:identifier" . (
;;;            (
;;;                ("tag_re" . "856")
;;;                ("subfield_re" . "u")
;;;                ("return_first_result_only" . t)
;;;            )
;;;            (
;;;                ("tag_re" . "02(0-9)")
;;;            )
;;;        ))
;;;        ("dc:isPartOf" . (
;;;            (
;;;                ("tag_re" . "533")
;;;                ("subfield_re" . "f")
;;;            )
;;;            (
;;;                ("tag_re" . "830")
;;;            )
;;;        ))
;;;        ("dc:language" . (
;;;            (
;;;                ("tag_re" . "034")
;;;            )
;;;        ))
;;;        ("dc:medium" . (
;;;            (
;;;                ("tag_re" . "338")
;;;            )
;;;        ))
;;;        ("dc:relation" . (
;;;            (
;;;                ("tag_re" . "730")
;;;                ("subfield_re" . "a")
;;;            )
;;;        ))
;;;        ("dc:subject" . (
;;;            (
;;;                ("tag_re" . "050")
;;;            )
;;;            (   ("tag_re" . "650")
;;;                ("subfield_re" . "(ax)")
;;;            )
;;;        ))
;;;        ("dc:title" . (
;;;            (
;;;                ("tag_re" . "130|240")
;;;            )
;;;            (
;;;                ("tag_re" . "245")
;;;                ("subfield_re" . "(ab)")
;;;            )
;;;        ))
;;;        ("dc.type" . (
;;;            (
;;;                ("tag_re" . "336")
;;;            )
;;;            (
;;;                ("tag_re" . "60(01)")
;;;                ("subfield_re" . "v")
;;;            )
;;;            (
;;;                ("tag_re" . "655")
;;;                ("filter" . (
;;;                    (
;;;                        ("subfield_re" . "2")
;;;                        ("value_re" . "^fast$")
;;;                    )
;;;                ))
;;;            )
;;;        ))
;;;        ("dcterms:alternative" . (
;;;            (
;;;                ("tag_re" . "246")
;;;            )
;;;        ))
;;;        ("dcterms:isssued" . (
;;;            (
;;;                ("tag_re" . "260")
;;;                ("subfield_re" . "c")
;;;            )
;;;            (
;;;                ("tag_re" . "264")
;;;                ("subfield_re" . "c")
;;;                ("indicator2_re" . "1")
;;;            )
;;;        ))
;;;        ("dcterms:location" . (
;;;            (
;;;                ("tag_re" . "260")
;;;                ("subfield_re" . "a")
;;;            )
;;;            (
;;;                ("tag_re" . "264")
;;;                ("subfield_re" . "a")
;;;                ("indicator2_re" . "1")
;;;            )
;;;            (
;;;                ("tag_re" . "533")
;;;                ("subfield_re" . "b")
;;;            )
;;;        ))
;;;        ("dcterms.publisher" . (
;;;            (
;;;                ("tag_re" . "260")
;;;                ("subfield_re" . "b")
;;;            )
;;;            (
;;;                ("tag_re" . "264")
;;;                ("subfield_re" . "b")
;;;                ("indicator2_re" . "1")
;;;            )
;;;        ))
;;;    ))
;;;)
;;;
